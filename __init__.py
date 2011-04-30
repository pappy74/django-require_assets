VERSION = (0, 1, 3)
__version__ = '.'.join(map(str, VERSION))

"""
0, 1, 3:
- Refactor and add tons of comments

0, 1, 2:
- BREAKING CHANGE: reorganized settings dict.  See docs for details.

0, 1, 1:
- added 'requires_style' template tag
- added 'static_url' setting
- bugfix: only one block requirement (per asset type) was actually being
  used
"""
import os, re, json
from django.conf import settings
from django.utils.encoding import smart_unicode

################################################################################
# Default Options
################################################################################
REQUIRES = {
    'asset_types': {
        # each asset type corresponds to an asset file extension
        'js': {
            # specify a template
            'template': "\t<script src='%s'></script>\n",

            # 'paths' allow you to customize asset locations based on type and
            # prefix. See docs for more details.
            'paths': { '': 'js/' },

            # these define the temporary 'token' that gets placed in the html.
            # Later on, those tokens get replaced with the actual asset html
            'token': '@@@JS:<GROUP>:<INDEX>@@@',

            # these define where in the html your assests get placed.  For
            # example, by default, js files get placed right before the </body>
            # tag.  They are organized by 'group'.
            'destination_tag': {
                'default': u'</body>',
                'inhead' : u'</head>',
            },
        },
        'css': {
            'template': "\t<link href='%s' rel='stylesheet'>\n",
            'paths': { '': 'css/' },
            'token': '@@@CSS:<GROUP>:<INDEX>@@@',
            'destination_tag': {
                'default': u'</head>',
            },
        },
    },

    # set this to the url your static files are hosted from
    'static_url': settings.STATIC_URL,
}

################################################################################
# Public interface
################################################################################

def get_assets(request):
    """
    Return a dictionary of assets required for a request.  Something like:
    {
        'js': ['foo.js'],
        'css': ['foo.css'],
    }
    """
    assets = {}
    for asset_type, asset_groups in requested_assets.get(request, {}).items():
        assets.setdefault(asset_type, [])
        for asset_list in asset_groups.values():
            for asset in asset_list:
                assets[asset_type].append( asset.getURL() )

    return assets

def requireFile(request, files, group='default'):
    """
    Require file assets.
    - files: an array of required files.  Asset type will be determined
      based on each file's extension.
    Returns:
    - a token to be inserted in to the HTML to indicate, "Assets required here"
    """
    tag = ""
    for filename in files:
        # distinguish between css and js files
        extension = os.path.splitext(filename)[1][1:].lower()

        tag += _add_req(request, group, extension, filename, filename=filename)
    return tag

def requireBlock(request, blocktype, content, name, group='default'):
    """
    Require block level assets.
    - blocktype: "script" or "style"
    - content: the actual content of the block.  Should not include the
      containing block tags (eg. <script></script>)
    - name: a unique name for this block.  If another block is required
      with the same name, it will be ignored.
    Returns either:
    - if request is AJAX, the rendered block (which will include
      <script>...</script>)
    - otherwise, a token to be inserted in to the HTML to indicate, "Asset XXX
      required here"
    """
    reqtype = {
        'script': 'js',
        'style': 'css',
    }[blocktype]

    tag = _add_req(request, group, reqtype, name, block=content )
    return tag


################################################################################
# Merge default options with specified settings
################################################################################

ASSET_DEFS = REQUIRES['asset_types']
ASSET_TYPES = ASSET_DEFS.keys() # simple array of asset types shortcut

if hasattr(settings, 'REQUIRES'):
    # update the asset types
    settings_types = settings.REQUIRES.get('asset_types', {})
    for asset_type, type_def in settings_types.items():
        if asset_type in ASSET_DEFS:
            # default asset type, update the default settings
            ASSET_DEFS[asset_type].update(type_def)
        else:
            # new asset_type, just add it
            ASSET_DEFS[asset_type] = type_def

    # if 'static_url' is specified, use it.
    for prop in ['static_url']:
        if prop in settings.REQUIRES:
            REQUIRES[prop] = settings.REQUIRES[prop]


################################################################################
# Set up module-wide variables
################################################################################

# 'requested_assets' stores the actual assets requested, organized by request,
# then asset_type, then group.
requested_assets = {}

# 'requested_assets_unique' stores each asset request in a flat dict.  Used to
# make sure assets are only used once per request
requested_assets_unique = {}

# 'token_regexes' stores a regex needed to scan for the tokens in the
# html processing step
token_regexes = {}
for asset_type, asset_info in ASSET_DEFS.items():
    token_regexes[asset_type] = {}
    for group in asset_info['destination_tag'].keys():
        token = asset_info['token']
        token = token.replace("<GROUP>", "(%s)" % group)
        token = token.replace("<INDEX>", '(\d+)')
        token_regexes[asset_type][group] = re.compile(token)

################################################################################
# Implementation
################################################################################

def _init_requested_assets(request):
    if not request in requested_assets:
        requested_assets[request] = {}
        requested_assets_unique[request] = {}
        for asset_type in ASSET_TYPES:
            requested_assets[request][asset_type] = {}
            for group in ASSET_DEFS[asset_type]['destination_tag'].keys():
                requested_assets[request][asset_type][group] = []

def _add_req(request, group, reqtype, unique_id, filename=None, block=None):
    """
    add a requirement (file or block)
    """
    # prep the dicts for this request/asset_type/group combination
    _init_requested_assets(request)
    requirements = requested_assets[request][reqtype][group]

    # only include each requirement once
    if unique_id and unique_id in requested_assets_unique[request]:
        return ""
    requested_assets_unique[request][unique_id] = True

    # build the appropriate request object
    # TODO: only js/css allowed right now
    if reqtype == "js":
        if filename:
            req = JSFile(filename)
        else:
            req = JSBlock(block)

    elif reqtype == "css":
        if filename:
            req = CSSFile(filename)
        else:
            req = CSSBlock(block)

    if request.is_ajax() and req.type == "block":
        return req.render()
    else:
        # build the token that gets embedded in the raw html
        token = ASSET_DEFS[reqtype]['token']
        token = token.replace("<GROUP>", group)
        token = token.replace("<INDEX>", str(len(requirements)))

        # finally, add the asset
        requirements.append( req )

        return token

class RequiresFileObj:
    asset_type = "" # this needs to be defined by the subclass
    type = "file"
    def __init__(self, filename):
        self.filename = filename

    def isFullURL(self):
        return re.match('^https?://', self.filename)

    def isAbsoluteURL(self):
        return self.filename.startswith("/")

    def getURL(self):
        if self.isFullURL() or self.isAbsoluteURL():
            # absolute URL with protocol/domain specified
            return self.filename

        if self.isAbsoluteURL():
            # absolute path on this domain
            return self.filename

        return self._path() + self.filename

    def render(self):
        return ASSET_DEFS[self.asset_type]['template'] % self.getURL()

    def isCompressible(self):
        return not self.isFullURL()

    def _path(self):
        """
        For a filename of "script.js", returns "/static/js/" (for example).  It
        does this by starting with the STATIC_URL (or whatever is defined in
        REQUIRES.static_url), then adding the entry of the first
        'REQUIRES.asset_types.paths' item that matches.

        This should only really be used by 'relative'-type filenames.
        """
        path = REQUIRES['static_url']

        # add paths as specified
        for prefix, subpath in self.getPrefixDict().items():
            if ( self.filename.startswith(prefix) ):
                path += subpath
                break;

        return path

    def getPrefixDict(self):
        return ASSET_DEFS[self.asset_type]['paths']

class RequiresBlockObj:
    type = "block"
    def __init__(self, block):
        self.block = block

    def isCompressible(self):
        return True

    def getURL(self):
        # added so blocks don't break 'get_assets'
        return ""

class CSSFile(RequiresFileObj):
    asset_type = "css"

class CSSBlock(RequiresBlockObj):
    asset_type = "css"
    def render(self):
        return "\t<style>%s</style>\n" % self.block

class JSFile(RequiresFileObj):
    asset_type = "js"

class JSBlock(RequiresBlockObj):
    asset_type = "js"
    def render(self):
        return "\t<script>%s</script>\n" % self.block

# Replace all of the embedded placeholders within an html string with
# link and script tags.
# By default, it grabs the individual file placeholders, keeping track
# of the order.  Then, it inserts a list of CSS link tags at the end of the
# "head" and a list of JS script tags at the end of the "body"
def process_html(request, html):
    if request in requested_assets:
        html = _fix_html_type(request, html, "css")
        html = _fix_html_type(request, html, "js")

        html = _add_list_of_assets(request, html)

        del requested_assets[request]
        del requested_assets_unique[request]
    return html

def _add_list_of_assets(request, html):
    assets = get_assets(request)
    tag = u"</head>"
    asset_string = "<script>var required_assets=%s;</script>"
    asset_string = asset_string % json.dumps(assets)
    html = html.replace(tag, unicode(asset_string) + tag)
    return html

def _fix_html_type(request, html, filetype):
    for group, files in requested_assets[request][filetype].items():

        # parse the content for the individual file tokens
        indices = []
        def sub_func(matchobj):
            indices.append(int(matchobj.group(2)))
            return ""

        regex = token_regexes[filetype][group]
        html = regex.sub(sub_func, html)

        # replace the 'replace me' tag with actual list of
        # 'tags' (ie <link href="foo.css">)
        file_html = u""
        uncompressible_html = u""
        for index in indices:
            fileObj = files[index]
            if fileObj.isCompressible():
                file_html += fileObj.render()
            else:
                uncompressible_html += fileObj.render()

        # try to use the provided 'compress' app to compress the output
        if hasattr(settings, 'COMPRESS') and settings.COMPRESS:
            # Currently this only supports the django-css app we use

            from django.template import Lexer,Parser,Token,TOKEN_TEXT
            file_html += "{% endcompress %}"
            lexer = Lexer(file_html, None)
            from compressor.templatetags.compress import compress
            file_html = compress(
                Parser(lexer.tokenize()),
                Token(TOKEN_TEXT, "compress " + filetype)
            ).render({})

        file_html = uncompressible_html + file_html
        tag = ASSET_DEFS[filetype]['destination_tag'].get(group, None)
        if tag:
            html = smart_unicode(html)
            html = html.replace(tag, file_html + tag)

    return html



VERSION = (0, 1, 0)
__version__ = '.'.join(map(str, VERSION))

"""
"""
import os, re
from django.conf import settings
from django.utils.encoding import smart_unicode

requires = {}

REQUIRES = {
    'js_template': "\t<script src='%s'></script>\n",
    'css_template': "\t<link href='%s' rel='stylesheet'>\n",
    'prefixes': {},
    'file_tokens': {
        'css': '@@@CSS:<GROUP>:<INDEX>@@@',
        'js': '@@@JS:<GROUP>:<INDEX>@@@',
    },
    'placeholder_tags': {
        'default': {
            'css': u'</head>',
            'js': u'</body>',
        },
        'inhead': {
            'js': u'</head>',
        }
    }
}

if hasattr(settings, 'REQUIRES'):
    # update the setting that are themselves dicts, first
    for setting in ['prefixes', 'file_tokens', 'placeholder_tags']:
        REQUIRES[setting].update(settings.REQUIRES.pop(setting, {}))

    # then update the rest
    REQUIRES.update(settings.REQUIRES)

token_regexes = {}

def set_request_key(request):
    #request.session['REQUEST_ID'] = uuid.uuid4()
    pass
def get_request_key(request):
    #return request.session['REQUEST_ID']
    return request

# require these file(s)
def requireFile(request, files, group='default'):
    # update prefixes
    tag = ""
    for filename in files:

        # distinguish between css and js files
        extension = os.path.splitext(filename)[1][1:].lower()

        # add prefixes as specified
        prefixes = REQUIRES['prefixes'].get(extension, {})
        for prefix, substitution in prefixes.items():
            if ( filename.startswith(prefix) ):
                filename = substitution + filename
                break

        tag += _add_req(request, group, extension, filename, filename=filename)
    return tag

def requireBlock(request, blocktype, content, name, group='default'):
    reqtype = {
        'script': 'js',
        'style': 'css',
    }[blocktype]

    tag = _add_req(request, group, reqtype, name, block=content )
    return tag

def _add_req(request, group, reqtype, unique_id, filename=None, block=None):
    """
    add a requirement (file or block)
    """
    key = get_request_key(request)

    # prep the dicts for this key/group combination
    requirements = requires.setdefault(key,{
        'unique': {},
        'groups': {},
    })['groups'].setdefault(group,{
        'css': [],
        'js': [],
    })
    unique_reqs = requires[key]['unique']

    # only include each requirement once
    if unique_id in unique_reqs:
        return ""
    unique_reqs[unique_id] = True

    # make sure we have regular expressions for each file token
    if not group in token_regexes:
        token_regexes[group] = {}
        for filetype,token in REQUIRES['file_tokens'].items():
            token = token.replace("<GROUP>", "(%s)" % group)
            token = token.replace("<INDEX>", '(\d+)')
            token_regexes[group][filetype] = re.compile(token)

    # add the requirement to the appropriate list
    index = len(requirements[reqtype])
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

    requirements[reqtype].append( req )

    # build the token that gets embedded in the raw html
    token = REQUIRES['file_tokens'][reqtype]
    token = token.replace("<GROUP>", group)
    token = token.replace("<INDEX>", str(index))
    return token

class RequiresFileObj:
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
            
        return self.path() + self.filename

    def isCompressible(self):
        return not self.isFullURL()
        
    def path(self):
        return ""

class RequiresBlockObj:
    def __init__(self, block):
        self.block = block

    def isCompressible(self):
        return True

class CSSFile(RequiresFileObj):
    def render(self):
        return REQUIRES['css_template'] % self.getURL()

    def path(self):
        return settings.MEDIA_URL + "css/"

class CSSBlock(RequiresBlockObj):
    def render(self):
        return "\t<style>%s</style>\n" % self.block

class JSFile(RequiresFileObj):
    def render(self):
        return REQUIRES['js_template'] % self.getURL()

    def path(self):
        return settings.MEDIA_URL + "js/"

class JSBlock(RequiresBlockObj):
    def render(self):
        return "\t<script>%s</script>\n" % self.block

# Replace all of the embedded placeholders within an html string with
# link and script tags.
# By default, it grabs the individual file placeholders, keeping track
# of the order.  Then, it inserts a list of CSS link tags at the end of the
# "head" and a list of JS script tags at the end of the "body"
def process_html(request, html):
    request_key = get_request_key(request)
    if request_key in requires:
        html = _fix_html_type(request_key, html, "css")
        html = _fix_html_type(request_key, html, "js")
        del requires[request_key]
    return html

def _fix_html_type(request_key, html, filetype):
    for group, filesbytype in requires[request_key]['groups'].items():
        files = filesbytype[filetype]

        # parse the content for the individual file tokens
        indices = []
        def sub_func(matchobj):
            indices.append(int(matchobj.group(2)))
            return ""
        regex = token_regexes[group][filetype]
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
        tag = REQUIRES['placeholder_tags'][group].get(filetype, None)
        if tag:
            html = smart_unicode(html)
            html = html.replace(tag, file_html + tag)

    return html



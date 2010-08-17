VERSION = (0, 1, 0)
__version__ = '.'.join(map(str, VERSION))

"""
"""
import os, re
from django.conf import settings
from django.utils.encoding import smart_unicode

requires = {}

# TODO: make these 'settings'
REQUIRES = {
    'js_template': "\t<script src='"+settings.MEDIA_URL+"js/%s'></script>\n",
    'css_template': "\t<link href='"+settings.MEDIA_URL+"css/%s' rel='stylesheet'>\n",
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
def requireFile(request, files, group="default"):
    key = get_request_key(request)
    #print "%s" % files

    # make sure we have regular expressions for each file token
    if not group in token_regexes:
        token_regexes[group] = {}
        for filetype,token in REQUIRES['file_tokens'].items():
            token = token.replace("<GROUP>", "(%s)" % group)
            token = token.replace("<INDEX>", '(\d+)')
            token_regexes[group][filetype] = re.compile(token)

    # set up a shortcut var to handle each file we need to add
    required_files = requires.setdefault(key,{
        'unique': {},
        'groups': {},
    })['groups'].setdefault(group,{
        'css': [],
        'js': [],
    })
    unique_files = requires[key]['unique']

    replace_with = ""
    for filename in files:
        
        # distinguish between css and js files
        extension = os.path.splitext(filename)[1][1:].lower()
        
        # add prefixes as specified
        prefixes = REQUIRES['prefixes'].get(extension, {})
        for prefix, substitution in prefixes.items():
            if ( filename.startswith(prefix) ):
                filename = substitution + filename
                break

        # only include each file once
        if filename in unique_files:
            continue
        unique_files[filename] = True

        # add the file to the appropriate list
        index = len(required_files[extension])
        if extension == "js":
            required_files[extension].append(JSFile(filename))
        elif extension == "css":
            required_files[extension].append(CSSFile(filename))

        # generate a 'token' that will be rendered in the HTML
        # until the middleware does its pass
        file_token = REQUIRES['file_tokens'][extension]
        file_token = file_token.replace("<GROUP>", group)
        file_token = file_token.replace("<INDEX>", str(index))
        replace_with += file_token
    
    return replace_with

class CSSFile:
    def __init__(self, filename):
        self.filename = filename
    
    def render(self):
        return REQUIRES['css_template'] % self.filename
        
class JSFile:
    def __init__(self, filename):
        self.filename = filename

    def render(self):
        return REQUIRES['js_template'] % self.filename
                
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
        for index in indices:
            fileObj = files[index]
            file_html += fileObj.render()

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

        tag = REQUIRES['placeholder_tags'][group].get(filetype, None)
        if tag:
            html = smart_unicode(html)
            html = html.replace(tag, file_html + tag)
    
    return html

              
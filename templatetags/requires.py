from django import template
from django.conf import settings
import os.path
import logging

from requires_js_css import requireFile, requireBlock

register = template.Library()

# use this to indicate your js or css files are necessary
# Eg: {% requires foo.js jquery.extension.js bar.css %}
@register.tag
def requires(parser, token):
    files = token.contents.split()[1:]

    group = "default"
    if not "." in files[0]:
        group = files.pop(0)

    #logging.debug("Requires: [%s]: %s" % (group, str(files) ))

    if len(files) < 1:
        raise template.TemplateSyntaxError, "%r tag requires at least one argument" % token.contents.split()[0]

    return RequiresNode( group, files )

# use this in include some javascript declared inline.  If an optional 'name'
# parameter is provided, the script will only get included once
@register.tag
def requires_script(parser, token):
    name = None
    try:
        args = token.split_contents()[1:]
    except IndexError:
        pass
        
    group = "'default'"
    name = None
    for arg in args:
        if "=" in arg:
            key,value = arg.split("=")
            if key == 'group':
                group = value
        else:
            name = arg
            
    nodelist = parser.parse(('endrequires_script',))
    parser.delete_first_token()
    return RequiresBlockNode( "script", group, name, nodelist )
    
class RequiresNode(template.Node):
    def __init__(self, group, files):
        self.files = files
        self.group = group
        
    def render(self, context):
        try:
            request = context["request"]
        except:
            logging.error("No request object found: %s" % str(self.files))
            return ""
        tag = requireFile(request, self.files, self.group)
        return tag

class RequiresBlockNode(template.Node):
    child_nodelists = ('nodelist',)
    def __init__(self, blocktype, group, name, nodelist):
        self.type = blocktype
        self.group = template.Variable(group)
        self.name = name
        self.nodelist = nodelist
    def render(self, context):
        try:
            request = context["request"]
        except:
            logging.error("No request object found: %s" % str(self.files))
            return ""

        content = self.nodelist.render(context)
        group = self.group.resolve(context)
        tag = requireBlock(request, self.type, content, self.name, group)
        return tag

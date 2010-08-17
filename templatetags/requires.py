from django import template
from django.conf import settings
import os.path
import logging

from requires_js_css import requireFile

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

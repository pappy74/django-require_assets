Django requires_js_css
======================

The goal of django-requires_js_css is to provide a way for individual templates to include their own JavaScript and CSS files, while at the same time adhering to site performance best practices.

For example, if you have a 'cool button' widget requested via a templatetag and defined by 'cool_button.html', you can specify 'cool_button.css' in the 'cool_button.html' file itself, and the css file will actually be loaded in the "HEAD" where it belongs (this is customizable though).

What this does *not* do is attempt to compress your JS/CSS or fix static directories on its own.  The hope is that requires_js_css will live side-by-side with the various compression apps, although with the current implementation, requires_js_css has to know about and explicitly call into each individual one.  Not sure yet how to fix this.

There is still a ton left to do here, and I plan on continuing work on it in the upcoming months.

- Document, document, document.
- Add test cases
- Allow named CSS 'blocks' and not just files
- Change parameters to be resolvable
- Allow more customization of 'groups'
- Support more than just django-css for compression/compiling
- Support CSS media attribute
- After all this is done, probably go back and refactor the whole danged thing :)

BASIC USAGE
************
- Add the app to the 'middleware' and 'apps' lists in your settings file.
- In your template file::

    {% load requires %}
    {% requires cool_button.css cool_button.js %}
    
That's it.  Your response will look something like::

    <html>
        <head>
        ...
        <link href="<MEDIA_URL>/css/cool_button.css" rel='stylesheet' />
        </head>
        <body>
        ...
        <script src='<MEDIA_URL>/js/cool_button.js'></script>
        </body>
    </html>

API
***
Template Tags
-------------
{% requires [<group>] <file1> <file2> ... <fileN> %}

group can be 

- default: load CSS in the head and JS before the closing BODY tag
- inhead: used to load JS in the head

file can be

- fully-qualified URL (eg. http://www.example.com/js/script.js)
- absolute URL (eg. /other_scripts/script.js)
- relative URL (eg. script.js) - using this triggers prefix composition

{% requires_script [<name>] %}<javascript>{% endrequires_script %}

- name is optional.  If given, the named javascript block will only be included once.

NOTES
*****

- No file will ever be requested more than once
- if COMPRESS=True, it will try to use django-css/django-compressor to compress your files
- there is a very crude mechanism of automatically prepending certain files with arbitrary text/pathnames.  I found this very useful for things like jquery.
- there is a very crude method of 'grouping' sets of files.  Right now, the only one of note is 'inhead' which is a tag you can apply to a JS requirement to add the script tag in the response HEAD: {% requires inhead jquery-1.4.2.js %}
- ordering of files *should* "just work", but I'm guessing there will be problematic edge cases.
- Yes, this *will* work if you render a template within view code, grab the response content and embed it within another template.  Although said pattern is hacky and should never, ever, ever be used.  Um... *cough*... yeah ;)


UPDATES
*******

2010-10-23
----------
- absolute paths on the current domain can now be specified (thanks silent1mezzo!)

2010-10-20
----------
- absolute URIs can now be required.  They will not have MEDIA_URL prepended (obviously), will not be 'compressed', and are included within their group in the response before any compressed content.
- New templatetag 'requires_script'.  Use this to require a block of JavaScript.  Takes an optional 'name' parameter.  

Ideas, criticisms and offers of help are all, of course, greatly appreciated.
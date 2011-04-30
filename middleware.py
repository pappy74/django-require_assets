from requires_js_css import process_html

class RequiresMiddleware:
    def process_response(self, request, response):
        #print "@@requires_js_css process_response"
        response.content = process_html(request, response.content)
        return response

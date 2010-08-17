from requires_js_css import set_request_key, process_html

class RequiresMiddleware:
    def process_request(self, request):
        #print "@@process_request"
        # set a unique ID for this request
        set_request_key(request)
        return None
        
    def process_response(self, request, response):
        #print "@@requires_js_css process_response"
        response.content = process_html(request, response.content)
        return response

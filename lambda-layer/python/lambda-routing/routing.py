from functools import wraps
import json
import re

class PathNotFoundError(Exception):
    pass

class VerbNotFoundError(Exception):
    pass

class UserRoleNotPermitted(Exception):
    pass

class UserNotAuthenticated(Exception):
    pass

class _RouteRegistry(object):

    def __init__(self):
        self.registry = {}
        self.perm_registry = {}

    def register_route(self, verb, path, func, required_roles):

        if not path in self.registry:
            self.registry[path] = {}
            self.perm_registry[path] = {}

        self.registry[path][verb] = func
        self.perm_registry[path][verb] = required_roles

    def match_route(self, request):

        resourcePath = request["requestContext"]["resourcePath"]
        verb = request["requestContext"]["httpMethod"]
        request_params = request["pathParameters"]


        resolved_path = self.registry.get(resourcePath, None)

        if not resolved_path:
            raise PathNotFoundError("Route for {resourcePath} not found".format(resourcePath=resourcePath))
        
        if not verb in self.registry[resolved_path]: #We know we'll get a hit for the resourcePath because we would have raised out otherwise
            raise VerbNotFoundError("{verb} not found for {resourcePath}".format(verb=verb, resourcePath=resourcePath))

        return {
            "function": self.registry[resolved_path][verb], 
            "perms": self.perm_registry[resolved_path][verb],
        }


    def check_perms(self, perms, user):
        if not user:
            raise UserNotAuthenticated("You must login")
        else:
            found = False
            for role in user.roles:
                if role in perms:
                    found = True
                    break
            if not found:
                raise UserRoleNotPermitted("You do not have a required role")


    def match_and_execute_route_for_gateway(self, request, user=None):

        request_params = request.get("pathParameters", {}) or {}
        query_params = request.get("queryStringParameters", {}) or {}
        request_params.update(query_params)
        extra_headers = {}

        matched_route = self.match_route(request)
        matched_function = matched_route["function"]
        matched_perms = matched_route["perms"]

        try:
            if matched_perms:
                self.check_perms(matched_perms, user)

            if request["requestContext"]["httpMethod"] in ("POST", "PATCH"):
                body = matched_function(json.loads(request["body"]), **request_params)
            else:
                body = matched_function(**request_params)
            status_code = 200
        except Exception as e:
            status_code = 500
            body = json.dumps(
                    {
                        'errorMessage': str(e),
                        'errorType': "APIError",
                        'stackTrace': []
                    }
                )
            extra_headers = {'X-Amzn-ErrorType':'APIError'}
        except TypeError as e:
            status_code = 500
            body = json.dumps(
                    {
                        'errorMessage': 'Unexpected path variable or querystring parameter',
                        'errorType': 'MalformedRequestError',
                        'stackTrace': []
                    }
                )
            extra_headers = {'X-Amzn-ErrorType':'MalformedRequestError'}

        extra_headers.update({ 'Content-Type': 'application/json' })

        if not isinstance(body, str): 
            # Sometimes a route may want to return headers (or just a plain object)
            # So we'll do the escaping for them and pop the headers off
            if isinstance(body, dict) and "headers" in body and "body" in body:
                extra_headers.update(body.pop("headers"))
                body = body.pop("body")

            body = json.dumps(body)

        return {
            'statusCode': status_code,
            'headers': extra_headers,
            'body': body
        }

RouteRegistry = _RouteRegistry()

class route(object):

    def __init__(self, path, verb, required_roles=None):

       self.path = path
       self.verb = verb
       self.required_roles = required_roles

    def __call__(self, func):

        RouteRegistry.register_route(verb=self.verb, path=self.path, func=func, required_roles=self.required_roles)

        @wraps(func)
        def wrapped(*args, **kwargs):

            func(*args, **kwargs)

        return wrapped
        
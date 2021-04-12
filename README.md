# lambda-rest
 An AWS lambda REST library

## How to use

Zip the python directory under lambda-layer, and upload it as a lambda-layer. Then, in your lambda, you can import `from lambda-routing.routing import RouteRegistry, Route`

In the lambda itself, you can update your lambda_handler to return `RouteRegistry.match_and_execute_route_for_gateway(event, user=user)` where user is a user object that you can create that minimally has a `roles` list property.

You can decorate functions inside of your lambda with `@route` like so:

```
@route("/path_to_resource/{resource_id}", "GET", required_roles=['user'])
def get_resource(resource_id):
    pass
```

`@route` will resolve any path variables into keyword variables, and for methods that take a request body (e.g. `POST`, `PATCH`, `UPDATE`), it will insert a positional variable as the first argument to the decorated function.

Non-string values will be automatically correctly serialized, and if you provide both `headers` and `body` values in a returned dict, it will pop the headers and send them as part of the response, and correctly serialize the body.

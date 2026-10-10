import asyncio
from starlette.responses import JSONResponse


class RequestRejected(Exception):
    def __init__(self, status):
        self.status = status


class ResourceLimitMiddleware:
    def __init__(self, app, max_concurrent=64, max_body=65536, max_response=4194304, body_timeout=10):
        self.app = app
        self.active = 0
        self.max_concurrent = max_concurrent
        self.max_body = max_body
        self.max_response = max_response
        self.body_timeout = body_timeout

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or not scope['path'].startswith('/api/v1/'):
            return await self.app(scope, receive, send)
        if scope['path'] == '/api/v1/system/health':
            return await self.app(scope, receive, send)
        if self.active >= self.max_concurrent:
            return await JSONResponse({'detail': 'Server busy'}, status_code=503, headers={'Retry-After': '1'})(scope, receive, send)
        if len(scope.get('query_string', b'')) > 8192:
            return await JSONResponse({'detail': 'Query too large'}, status_code=414)(scope, receive, send)
        self.active += 1
        body_size = 0
        response_size = 0
        messages = []
        rejected_status = None

        async def limited_receive():
            nonlocal body_size, rejected_status
            try:
                message = await asyncio.wait_for(receive(), timeout=self.body_timeout)
            except TimeoutError:
                rejected_status = 408
                raise RequestRejected(408)
            body_size += len(message.get('body', b''))
            if body_size > self.max_body:
                rejected_status = 413
                raise RequestRejected(413)
            return message

        async def limited_send(message):
            nonlocal response_size
            response_size += len(message.get('body', b''))
            if response_size > self.max_response:
                raise RequestRejected(503)
            messages.append(message)

        try:
            lengths = [value for key, value in scope.get('headers', []) if key.lower() == b'content-length']
            if lengths:
                try:
                    if any(int(value) > self.max_body for value in lengths):
                        raise RequestRejected(413)
                except ValueError:
                    raise RequestRejected(400)
            await self.app(scope, limited_receive, limited_send)
            if rejected_status:
                raise RequestRejected(rejected_status)
            for message in messages:
                await send(message)
        except RequestRejected as error:
            await JSONResponse({'detail': 'Request exceeds server limits'}, status_code=error.status)(scope, receive, send)
        finally:
            self.active -= 1

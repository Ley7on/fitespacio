from django.http import HttpResponse

class RootRedirectMiddleware:
    """Middleware que redirige la raíz (/) a /login/"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si la ruta es exactamente '/', redirige a login
        if request.path == '/' or request.path == '':
            return self._redirect_to_login()
        
        response = self.get_response(request)
        return response
    
    def _redirect_to_login(self):
        """Genera HTML para redirigir a /login/"""
        html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>FitSpace - Redirecting</title>
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            height: 100vh; 
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #4f46e5 100%);
            margin: 0;
        }
        .container {
            text-align: center;
            color: white;
        }
        .spinner {
            border: 4px solid rgba(255, 255, 255, 0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    <script>
        // Redirigir inmediatamente sin cachear
        window.location.replace('/login/');
    </script>
</head>
<body>
    <div class="container">
        <div class="spinner"></div>
        <p>Redirigiendo a login...</p>
    </div>
</body>
</html>'''
        response = HttpResponse(html)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Content-Type'] = 'text/html; charset=utf-8'
        return response

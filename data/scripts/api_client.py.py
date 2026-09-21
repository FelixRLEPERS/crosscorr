class DataClient:
    def __init__(self, api_key):
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {api_key}'})
        # Здесь происходит инициализация клиента

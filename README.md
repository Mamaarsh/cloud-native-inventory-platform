# Cloud Native Inventory Platform

A production-oriented inventory and order management platform built with Django REST Framework, PostgreSQL, Docker, and cloud-native principles.

## Features

- Django REST Framework API
- JWT Authentication
- Role-Based Access Control (RBAC)
- Product & Warehouse Management
- Inventory Tracking
- Order Management
- Order Status Workflow
- Swagger / OpenAPI Documentation
- PostgreSQL Integration


## Technologies

- Python
- Django
- Django REST Framework
- PostgreSQL
- Docker
- JWT
- Kubernetes (planned)
- CI/CD (planned)
- Prometheus & Grafana (planned)


## Architecture

Client → Django REST API → Authentication & RBAC → Business Logic → PostgreSQL


## Documentation

- [Architecture Documentation](docs/architecture.md)
- [API Documentation](docs/api.md)


## Installation

Clone the repository:

git clone https://github.com/Mamaarsh/cloud-native-inventory-platform.git

Install dependencies:

pip install -r requirements.txt

Run migrations:

python manage.py migrate

Create roles:

python manage.py create_roles

Run application:

python manage.py runserver


## Testing

Run tests:

python manage.py test


## Roadmap

- Production Docker Compose
- CI/CD Pipeline
- Kubernetes Deployment
- Monitoring with Prometheus & Grafana
- Centralized Logging


## License

MIT License

See [LICENSE](LICENSE) for details.


## Author

Mohammad Arshia Jafari

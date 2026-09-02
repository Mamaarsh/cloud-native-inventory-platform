# Cloud Native Inventory Platform

A DevOps-focused cloud-native inventory and order management platform built with Django REST Framework, PostgreSQL, Docker, and modern infrastructure practices.

The main goal of this project is to demonstrate a complete DevOps workflow, including application development, containerization, CI/CD automation, Kubernetes deployment, monitoring, logging, and production-ready infrastructure design.


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
- Health Check Endpoints


## Technologies

### Application

- Python
- Django
- Django REST Framework
- PostgreSQL
- JWT


### DevOps & Cloud Native

- Docker
- CI/CD Pipeline (planned)
- Kubernetes (planned)
- Helm Charts (planned)
- Prometheus & Grafana (planned)
- Centralized Logging (planned)


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

The project includes tests for:

- Authentication
- RBAC Permissions
- Order Creation
- Order Workflow
- Health Checks


Run tests:

python manage.py test


## Roadmap

### DevOps Roadmap

- Production Docker Compose
- CI/CD Automation
- Docker Image Registry
- Kubernetes Deployment
- Helm Charts
- Monitoring with Prometheus & Grafana
- Centralized Logging
- Disaster Recovery


## License

MIT License

See [LICENSE](LICENSE) for details.


## Author

Mohammad Arshia Jafari

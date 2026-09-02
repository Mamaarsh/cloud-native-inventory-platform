# Cloud Native Inventory Platform

## Description

This project is a production-oriented inventory and order management platform built with Django REST Framework and PostgreSQL.

The system provides a secure and scalable REST API for managing products, warehouses, inventory operations, and orders.

The implementation focuses on clean architecture, JWT authentication, Role-Based Access Control (RBAC), transactional business logic, and cloud-native development practices.

---

## Features

- RESTful API built with Django REST Framework
- Secure JWT authentication and authorization
- Role-Based Access Control (RBAC)
- Product management
- Warehouse management
- Inventory tracking
- Order management
- Transaction-safe order creation
- Order status workflow
- PostgreSQL database integration
- Swagger / OpenAPI documentation
- Health check endpoints


---

## Technologies Used

### Backend

- Python
- Django
- Django REST Framework
- PostgreSQL
- JWT Authentication


### DevOps

- Docker
- Git
- CI/CD (planned)
- Kubernetes (planned)
- Prometheus & Grafana (planned)


---

## Authorization Roles

The system implements the following roles:

- Admin
- Warehouse Manager
- Operator
- Auditor


---

## Architecture

The application follows a layered architecture:

Client

↓

Django REST API

↓

Authentication & Authorization Layer

↓

Business Logic Layer

↓

PostgreSQL Database


Detailed documentation:

- Architecture: docs/architecture.md
- API Reference: docs/api.md


---

## API Documentation

Swagger UI:

/api/docs/


OpenAPI Schema:

/api/schema/


---

## Installation

1. Clone the repository:

git clone https://github.com/Mamaarsh/cloud-native-inventory-platform.git


2. Navigate to backend directory:

cd cloud-native-inventory-platform/application/backend


3. Install dependencies:

pip install -r requirements.txt


4. Configure environment variables:

cp .env.example .env


5. Apply migrations:

python manage.py migrate


6. Create default roles:

python manage.py create_roles


7. Run the development server:

python manage.py runserver


---

## Testing

The project includes tests for:

- Authentication
- JWT flow
- RBAC permissions
- Order creation
- Order workflow
- Health checks


Run tests:

python manage.py test


---

## Roadmap

### Application

[x] Backend foundation

[x] JWT Authentication

[x] RBAC Authorization

[x] Inventory Management

[x] Order Management

[x] Order Workflow


Upcoming:

[ ] Stock Management

[ ] Payment Module

[ ] Notification Service


### DevOps

Upcoming:

[ ] Production Docker Compose

[ ] CI/CD Pipeline

[ ] Kubernetes Deployment

[ ] Helm Charts

[ ] Prometheus Monitoring

[ ] Grafana Dashboards

[ ] Centralized Logging


---

## Documentation

- Architecture Documentation: docs/architecture.md
- API Documentation: docs/api.md


---

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request.


---

## License

This project is licensed under the MIT License.

See the LICENSE file for details.


---

## Author

- Mohammad Arshia Jafari - Backend Developer

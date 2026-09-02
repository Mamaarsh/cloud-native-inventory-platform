# Cloud Native Inventory Platform

A production-oriented inventory and order management platform built with Django REST Framework, PostgreSQL, Docker, and cloud-native principles.

This project demonstrates backend engineering practices and DevOps workflows including authentication, authorization, containerization, CI/CD, Kubernetes, monitoring, and observability.

---

## 🚀 Features

### Backend

- Django REST Framework API
- PostgreSQL Database
- Custom Django User Model
- JWT Authentication
- Role-Based Access Control (RBAC)
- Swagger / OpenAPI Documentation


### Business Features

- Product Management
- Warehouse Management
- Inventory Tracking
- Order Management
- Transaction-safe Order Creation
- Order Status Workflow


### Authorization Roles

- Admin
- Warehouse Manager
- Operator
- Auditor


---

## 🛠️ Tech Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- JWT
- Docker
- Git
- Kubernetes (planned)
- CI/CD (planned)
- Prometheus & Grafana (planned)


---

## 🏗️ Architecture

The application follows a layered architecture:

Client → Django REST API → Authentication & RBAC → Business Logic Layer → PostgreSQL


Main components:

- API Layer: Handles requests, validation, serialization, authentication, and permissions.
- Business Logic Layer: Contains application rules such as order workflow and transaction management.
- Data Layer: Uses Django ORM with PostgreSQL.


Detailed documentation:

- docs/architecture.md
- docs/api.md


---

## 📚 API Documentation

Swagger UI:

/api/docs/


OpenAPI Schema:

/api/schema/


---

## ▶️ Run Locally

Clone repository:

git clone https://github.com/Mamaarsh/cloud-native-inventory-platform.git


Install dependencies:

pip install -r requirements.txt


Apply migrations:

python manage.py migrate


Create default roles:

python manage.py create_roles


Run application:

python manage.py runserver


---

## 🧪 Testing

Implemented tests cover:

- JWT Authentication
- RBAC Permissions
- Order Creation
- Order Status Workflow
- Health Checks


Run tests:

python manage.py test


---

## 🗺️ Roadmap

Application:

✅ Backend Foundation  
✅ JWT Authentication  
✅ RBAC Authorization  
✅ Inventory Management  
✅ Order Management  
✅ Order Workflow  

Upcoming:

⬜ Stock Management  
⬜ Payment Module  
⬜ Notification Service  


DevOps:

⬜ Production Docker Compose  
⬜ CI/CD Pipeline  
⬜ Kubernetes Deployment  
⬜ Helm Charts  
⬜ Prometheus Monitoring  
⬜ Grafana Dashboards  
⬜ Centralized Logging


---

## 📖 Documentation

- Architecture: docs/architecture.md
- API Reference: docs/api.md


---

## License

MIT License

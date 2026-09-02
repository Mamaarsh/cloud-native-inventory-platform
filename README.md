# Cloud Native Inventory Platform

A production-oriented inventory and order management platform built with Django REST Framework, PostgreSQL, Docker, and cloud-native principles.

This project demonstrates backend engineering practices and DevOps workflows including authentication, authorization, containerization, CI/CD, Kubernetes, monitoring, and observability.

---

## 🚀 Features

## Backend

- Django REST Framework API
- PostgreSQL Database
- Custom Django User Model
- JWT Authentication
- Role-Based Access Control (RBAC)
- Swagger / OpenAPI Documentation


## Business Features

- Product Management
- Warehouse Management
- Inventory Tracking
- Order Management
- Transaction-safe Order Creation
- Order Status Workflow


## Authorization Roles

Implemented roles:

- Admin
- Warehouse Manager
- Operator
- Auditor


---

# 🏗️ Architecture

The system follows a layered architecture:

Client

↓

Django REST API

↓

JWT Authentication + RBAC

↓

Business Logic Layer

↓

PostgreSQL Database


Main components:

- API Layer:
  Handles HTTP requests, validation, serialization, authentication, and permissions.

- Business Logic Layer:
  Contains application rules such as order workflow and transaction management.

- Data Layer:
  Uses Django ORM with PostgreSQL for persistent storage.


Detailed documentation:

- Architecture: docs/architecture.md
- API Reference: docs/api.md


---

# 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Backend | Python, Django, Django REST Framework |
| Database | PostgreSQL |
| Authentication | JWT |
| Authorization | RBAC |
| Containerization | Docker |
| API Documentation | Swagger / OpenAPI |
| Future Infrastructure | Kubernetes, CI/CD, Monitoring |


---

# 📚 API Documentation

Swagger UI:

/api/docs/


OpenAPI Schema:

/api/schema/


Full API documentation:

docs/api.md


---

# ▶️ Running Locally

Clone repository:

git clone https://github.com/Mamaarsh/cloud-native-inventory-platform.git


Navigate to backend:

cd application/backend


Install dependencies:

pip install -r requirements.txt


Create environment file:

cp .env.example .env


Run migrations:

python manage.py migrate


Create default roles:

python manage.py create_roles


Run application:

python manage.py runserver


---

# 🧪 Testing

The project includes tests for:

- JWT Authentication
- RBAC Permissions
- Order Creation
- Order Status Workflow
- Health Checks
- API Validation


Run tests:

python manage.py test


---

# 🗺️ Roadmap

## Application

✅ Backend Foundation  
✅ PostgreSQL Integration  
✅ JWT Authentication  
✅ RBAC Authorization  
✅ Inventory Management  
✅ Order Management  
✅ Order Workflow  


Upcoming:

⬜ Stock Management  
⬜ Payment Module  
⬜ Notification Service  
⬜ Performance Optimization  


---

## DevOps

Upcoming:

⬜ Production Docker Compose  
⬜ CI/CD Pipeline  
⬜ Docker Image Registry  
⬜ Kubernetes Deployment  
⬜ Helm Charts  
⬜ Prometheus Monitoring  
⬜ Grafana Dashboards  
⬜ Centralized Logging  
⬜ Disaster Recovery Strategy  


---

# 📖 Documentation

Architecture:

docs/architecture.md


API Reference:

docs/api.md


---

# 🎯 Project Goal

This project demonstrates practical experience with:

- Backend Engineering
- REST API Design
- Database Architecture
- Secure Application Development
- Containerization
- Cloud Native Deployment
- DevOps Automation


---

# License

MIT License

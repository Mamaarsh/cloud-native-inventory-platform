# Cloud Native Inventory Platform

A production-oriented inventory and order management platform built with Django REST Framework, PostgreSQL, Docker, and cloud-native architecture principles.

This project demonstrates backend engineering practices combined with DevOps workflows, including secure API design, containerization, CI/CD, Kubernetes deployment, monitoring, and observability.

---

# Overview

Cloud Native Inventory Platform is a backend system designed for managing products, warehouses, inventory levels, and customer orders.

The project follows production-oriented principles:

- Clean backend architecture
- Secure authentication and authorization
- Transaction-safe business logic
- Service layer architecture
- REST API design
- Containerized deployment
- Cloud-native infrastructure roadmap

---

# Implemented Features

## Authentication

Implemented:

- Custom Django User Model
- JWT authentication
- Access and refresh tokens
- Current user API endpoint


## Authorization (RBAC)

Implemented role-based access control using Django Groups and Permissions.

Available roles:

- Admin
- Warehouse Manager
- Operator
- Auditor


Features:

- Group-based authorization
- API-level permission enforcement
- Protected resources based on user roles


## Inventory Management

Implemented:

- Product management
- Warehouse management
- Inventory tracking
- Product availability handling


## Order Management

Implemented:

- Nested order creation
- Order items
- Historical product price snapshots
- User-owned orders
- Transaction-safe order creation


## Order Status Workflow

Implemented order lifecycle management:

pending → processing → shipped → delivered

Additional transition:

pending → cancelled


Features:

- Dedicated status transition endpoint
- Transaction-safe status changes
- Database row locking using select_for_update
- Role-based workflow permissions

---

# API Documentation

OpenAPI documentation:

Swagger UI:

/api/docs/

ReDoc:

/api/redoc/

OpenAPI Schema:

/api/schema/

---

# Architecture

High-level architecture:

User

↓

Django REST API

↓

JWT Authentication + RBAC

↓

Application Services

↓

PostgreSQL Database

↓

Inventory + Orders + Users

---

# Technology Stack

## Backend

- Python 3.14
- Django 5.2
- Django REST Framework


## Database

- PostgreSQL


## Authentication

- JWT
- Django Authentication System


## Infrastructure

- Docker
- Gunicorn


## Planned DevOps Stack

- Docker Compose Production
- GitHub Actions
- Jenkins
- Kubernetes
- Helm
- Prometheus
- Grafana
- Centralized Logging

---

# Project Structure

cloud-native-inventory-platform

application/
 
    backend/
    
        config/
        
        inventory/
        
        users/
        
        Dockerfile
        
        requirements.txt


docs/

docker/

kubernetes/

monitoring/

README.md

---

# API Overview

## Authentication

POST /api/auth/token/

POST /api/auth/token/refresh/

GET /api/auth/me/


## Inventory

GET /api/v1/products/

GET /api/v1/warehouses/

GET /api/v1/inventory/


## Orders

Create order:

POST /api/v1/orders/


Change order status:

POST /api/v1/orders/{id}/change-status/

---

# Development Setup

Clone repository:

git clone https://github.com/Mamaarsh/cloud-native-inventory-platform.git


Navigate:

cd application/backend


Create virtual environment:

python -m venv .venv


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

# Testing

Run tests:

python manage.py test


Current test coverage includes:

- JWT authentication
- RBAC permissions
- Order creation
- Order workflow
- Health checks
- API behavior validation

---

# Roadmap

## Application

[x] Django backend foundation

[x] PostgreSQL integration

[x] Custom user model

[x] JWT authentication

[x] RBAC authorization

[x] Inventory models

[x] Order management

[x] Order status workflow


Upcoming:

[ ] Inventory stock management

[ ] Stock reservation system

[ ] Payment module

[ ] Notification service

[ ] Performance optimization


## DevOps

Upcoming:

[ ] Production Docker Compose

[ ] CI/CD pipeline

[ ] Docker image registry

[ ] Kubernetes deployment

[ ] Helm charts

[ ] Prometheus monitoring

[ ] Grafana dashboards

[ ] Centralized logging

[ ] Disaster recovery strategy

---

# Goals

This project demonstrates practical experience with:

- Backend engineering
- REST API development
- Database design
- Secure application architecture
- Containerization
- Cloud-native deployment
- DevOps automation

---

# License

MIT License
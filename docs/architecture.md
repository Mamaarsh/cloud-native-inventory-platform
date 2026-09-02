# System Architecture

## Overview

Cloud Native Inventory Platform is a production-oriented inventory and order management backend built with Django REST Framework.

The architecture is designed around clean separation of responsibilities, secure API access, transactional business logic, and future cloud-native deployment.

---

# High Level Architecture

The system follows this flow:

Client

↓

Django REST API

↓

Authentication & Authorization Layer

↓

Application Business Logic

↓

PostgreSQL Database


---

# Application Components

## API Layer

Implemented using Django REST Framework.

Responsibilities:

- Handle HTTP requests
- Validate input data
- Serialize and deserialize data
- Apply authentication and permissions
- Provide RESTful endpoints


Main components:

- ViewSets
- Serializers
- Permission classes


---

## Business Logic Layer

Business rules are separated from API views using service modules.

Example:

Order status workflow is handled by a dedicated service:

- Validate allowed transitions
- Ensure transactional updates
- Prevent invalid state changes


Implemented using:

- Service layer pattern
- transaction.atomic()
- select_for_update()


---

## Data Layer

The application uses Django ORM with PostgreSQL.

Main models:

- User
- Product
- Warehouse
- Inventory
- Order
- OrderItem


Database responsibilities:

- Persistent storage
- Data integrity
- Relationships
- Constraints


---

# Authentication Architecture

Authentication is implemented using JWT.

Flow:

1. User sends username and password.
2. API validates credentials.
3. Server returns access and refresh tokens.
4. Client uses access token for protected requests.


Implemented features:

- Custom Django User model
- JWT authentication
- Token refresh mechanism


---

# Authorization Architecture (RBAC)

Authorization is implemented using Django Groups and Permissions.


Available roles:

## Admin

Full access to inventory resources.


## Warehouse Manager

Can manage warehouse operations and update inventory.


## Operator

Can perform operational inventory tasks.


## Auditor

Read-only access for auditing purposes.


Permission checks are enforced at API level using DRF permission classes.

---

# Order Workflow Architecture

Order status follows a controlled state machine.


Supported transitions:

pending → processing

processing → shipped

shipped → delivered

pending → cancelled

processing → cancelled


Terminal states:

- delivered
- cancelled


Invalid transitions are rejected by the business layer.

---

# Current Infrastructure

Implemented:

- Django REST Framework backend
- PostgreSQL database
- Dockerized backend
- JWT authentication


Future DevOps implementation:

- Production Docker Compose
- CI/CD pipeline
- Kubernetes deployment
- Helm charts
- Monitoring with Prometheus and Grafana
- Centralized logging
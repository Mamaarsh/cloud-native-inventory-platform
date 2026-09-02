# API Documentation

## Overview

This document describes the REST API endpoints provided by the Cloud Native Inventory Platform.

The API is built using Django REST Framework and follows RESTful API principles.

Base URL:

/api/v1/

Authentication:

Protected endpoints use JWT Bearer authentication.

Authorization header format:

Authorization: Bearer <access_token>


---

# Authentication API

## Obtain JWT Token

Endpoint:

POST /api/auth/token/

Purpose:

Authenticate a user and receive access and refresh tokens.


Request:

{
    "username": "username",
    "password": "password"
}


Response:

{
    "access": "access_token",
    "refresh": "refresh_token"
}


---

## Refresh Access Token

Endpoint:

POST /api/auth/token/refresh/

Purpose:

Generate a new access token using a refresh token.


---

## Current User

Endpoint:

GET /api/auth/me/

Authentication:

Required


Purpose:

Returns information about the currently authenticated user.


---

# Products API

Products represent items managed by the inventory system.


## List Products

Endpoint:

GET /api/v1/products/


Purpose:

Retrieve available products.


Accessible roles:

- Admin
- Warehouse Manager
- Operator
- Auditor


---

## Create Product

Endpoint:

POST /api/v1/products/


Required role:

- Admin


---

## Update Product

Endpoint:

PUT /api/v1/products/{id}/

PATCH /api/v1/products/{id}/


Required role:

- Admin


---

## Delete Product

Endpoint:

DELETE /api/v1/products/{id}/


Required role:

- Admin


---

# Warehouse API

Warehouses represent physical storage locations.


## List Warehouses

Endpoint:

GET /api/v1/warehouses/


Accessible roles:

- Admin
- Warehouse Manager
- Operator
- Auditor


---

## Create Warehouse

Endpoint:

POST /api/v1/warehouses/


Required role:

- Admin


---

## Update Warehouse

Endpoint:

PATCH /api/v1/warehouses/{id}/


Required role:

- Admin


---

## Delete Warehouse

Endpoint:

DELETE /api/v1/warehouses/{id}/


Required role:

- Admin


---

# Inventory API

Inventory manages product quantities in warehouses.


## List Inventory

Endpoint:

GET /api/v1/inventory/


Accessible roles:

- Admin
- Warehouse Manager
- Operator
- Auditor


---

## Create Inventory Record

Endpoint:

POST /api/v1/inventory/


Allowed roles:

- Admin
- Warehouse Manager
- Operator


---

## Update Inventory Quantity

Endpoint:

PATCH /api/v1/inventory/{id}/


Allowed roles:

- Admin
- Warehouse Manager


---

## Delete Inventory Record

Endpoint:

DELETE /api/v1/inventory/{id}/


Allowed role:

- Admin


---

# Orders API

Orders represent customer purchase requests.


## Create Order

Endpoint:

POST /api/v1/orders/


Authentication:

Required


The authenticated user is automatically assigned as the order owner.


Request example:

{
    "items": [
        {
            "product": 1,
            "quantity": 3
        }
    ]
}


The system automatically:

- Creates the order
- Creates order items
- Stores historical product prices
- Assigns the authenticated user


---

## List Orders

Endpoint:

GET /api/v1/orders/


Accessible roles:

- Admin
- Warehouse Manager
- Operator
- Auditor


Filtering:

status

Example:

/api/v1/orders/?status=pending


Search fields:

- Username
- Email
- Product name
- Product SKU


Ordering:

- created_at
- updated_at
- status


---

## Order Detail

Endpoint:

GET /api/v1/orders/{id}/


Returns:

- Order information
- User information
- Order items
- Product details


---

# Order Status Workflow API

Order status changes are handled through a dedicated workflow endpoint.

Direct status modification through normal PATCH requests is disabled.


## Change Order Status

Endpoint:

POST /api/v1/orders/{id}/change-status/


Request:

{
    "status": "processing"
}


Supported transitions:

pending -> processing

processing -> shipped

shipped -> delivered

pending -> cancelled

processing -> cancelled


---

# Workflow Permissions

## Admin

Can perform all valid transitions.


## Warehouse Manager

Allowed transitions:

pending -> processing

processing -> shipped


## Operator

No permission.


## Auditor

No permission.


---

# Health Check API


## Liveness Check

Endpoint:

GET /api/health/live/


Purpose:

Checks whether the application is running.


---

## Readiness Check

Endpoint:

GET /api/health/ready/


Purpose:

Checks application dependencies such as database availability.


---

# API Documentation UI


Swagger UI:

/api/docs/


OpenAPI Schema:

/api/schema/


ReDoc:

/api/redoc/
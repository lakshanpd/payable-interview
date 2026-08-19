Used Claude Code with Sonnet 5

# CircleFund Technical Assessment

You are a senior full-stack engineer. Build a complete working implementation of the following application.

## Tech Stack

Backend:

* Django 5+
* Django REST Framework
* SQLite
* JWT Authentication using SimpleJWT

Mobile:

* React Native with Expo
* React Navigation
* Axios
* AsyncStorage for token persistence

## Requirements

Build a CircleFund application.

A CircleFund circle consists of up to 4 members.

Members contribute money into a shared pot every round.

Each round has one payout recipient.

The payout rotates according to member position order.

Only the circle admin can approve payouts.

The system must be safe against concurrent requests.

---

# Backend Requirements

## Authentication

Create the following endpoints:

POST /api/auth/register
POST /api/auth/login

Registration fields:

* username
* email
* password

Login returns JWT access token and refresh token.

All endpoints except register/login require authentication.

Use Django's User model or a custom user model.

---

# Database Design

Design normalized models.

Suggested entities:

## Circle

Fields:

* id
* name
* invite_code
* admin (FK User)
* contribution_amount
* penalty_rate
* max_members (default 4)
* created_at

## CircleMember

Fields:

* id
* circle
* user
* position
* joined_at

Rules:

* unique(circle,user)
* unique(circle,position)

Admin should automatically become position 1.

Members joining receive the next available position.

Maximum members = 4.

---

## Round

Fields:

* id
* circle
* payout_recipient
* status
* contribution_amount
* deadline
* payout_amount
* approved_at
* created_at

Status choices:

* OPEN
* PENDING_APPROVAL
* COMPLETED

Only one OPEN round should exist per circle.

---

## Contribution

Fields:

* id
* round
* member
* amount
* penalty
* total_paid
* is_late
* created_at

Constraint:

One contribution per member per round.

---

# Circle APIs

## Create Circle

POST /api/circles

Input:

{
"name": "My Circle",
"contribution_amount": 5000
}

Behavior:

* authenticated user becomes admin
* user becomes position 1
* generate unique invite code
* create first round automatically

Return circle details.

---

## Join Circle

POST /api/circles/join

Input:

{
"invite_code": "ABC123"
}

Behavior:

* find circle
* reject if circle full
* reject if user already joined
* assign next sequential position

Return membership details.

---

## Circle Details

GET /api/circles/{id}

Return:

* circle info
* member list
* current round
* contribution status per member

This endpoint will power the mobile screen.

---

# Round Logic

## Recipient Selection

Recipient should be:

The member with the smallest position that has not yet received a payout.

Example:

Position 1 -> Round 1 recipient
Position 2 -> Round 2 recipient
Position 3 -> Round 3 recipient
Position 4 -> Round 4 recipient

After everyone receives once, no additional rounds need to be created.

Implement helper service methods.

---

# Contribution Logic

Endpoint:

POST /api/rounds/{id}/contribute

Rules:

* recipient cannot contribute
* member can contribute only once
* calculate late penalties
* use integer math only

Penalty formula:

penalty = round_half_up(
contribution_amount * penalty_rate / 100
)

Examples:

5000 * 3 / 100 = 150

penalty = 150

total = 5150

Example:

3333 * 3 / 100 = 99.99

round_half_up => 100

total = 3433

Do not use float arithmetic.

Use Python Decimal with ROUND_HALF_UP.

Store all monetary values as integers.

---

# Round State Changes

After every contribution:

Check whether:

* all non-recipient members contributed

OR

* deadline passed

If true:

Move round status to:

PENDING_APPROVAL

Do not auto-complete.

---

# Admin Approval

Endpoint:

POST /api/rounds/{id}/approve

Rules:

* only circle admin can approve
* round must be PENDING_APPROVAL

Calculation:

final_payout_amount = floor(
sum(contributions.total_paid) * 0.99
)

Store payout amount.

Mark round COMPLETED.

Create next round automatically.

Next round recipient should be next unpaid member.

If everyone has already received payout:

Do not create another round.

---

# Concurrency Requirements

This is critical.

The solution must be safe against:

## Simultaneous Contributions

Two members may contribute at the exact same time.

## Double Approval

Admin may press Approve twice.

Use database transactions.

Use:

transaction.atomic()

and

select_for_update()

where appropriate.

The implementation must prevent:

* duplicate contributions
* double approval
* duplicate round creation
* corrupted totals

Do not use in-memory flags.

All protection must happen at the database level.

Implement comments explaining why locking is used.

---

# DRF Structure

Use:

apps/
users/
circles/
rounds/

Create:

* serializers
* views
* urls
* services
* permissions

Keep business logic out of views where possible.

Use service classes.

---

# Mobile App

Build using Expo.

Folder structure:

src/
screens/
navigation/
services/
hooks/
components/

---

# Screens

## Login Screen

Fields:

* email
* password

Store JWT token.

Navigate to circle screen after login.

---

## Circle Screen

Display:

Circle Name

Members List

For each member show:

* username
* position
* contribution status

Show current round status.

---

## Contribute Button

Visible only if:

* user is not recipient
* user has not contributed

Implement optimistic update:

1. Immediately mark as contributed
2. Send API request
3. If request fails:

   * rollback UI state
   * show inline error

---

## Approve Button

Visible only if:

* current user is admin
* round status is PENDING_APPROVAL

Pressing button calls approval endpoint.

Prevent repeated taps on frontend.

---

# API Documentation

Create:

README.md

Include:

* setup instructions
* migrations
* how to run backend
* how to run mobile app
* API endpoint list
* architecture decisions
* concurrency strategy
* assumptions

---

# Testing

Add tests for:

* registration
* login
* create circle
* join circle
* member limit
* contribution
* late penalty calculation
* approval permissions
* round rotation
* double approval protection

Use Django TestCase.

---

# Code Quality

Requirements:

* clean architecture
* type hints where possible
* meaningful comments
* production-style error handling
* no unnecessary complexity
* prioritize correctness over features

Generate complete source code with all files, migrations, serializers, views, services, urls, models, tests, and React Native screens.

## SQLite row-level locking Issue is missed by the AI agent

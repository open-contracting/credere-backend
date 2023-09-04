General
=======

Repository structure
--------------------------------

::

  app/                                      # Main application module
  │ ├── main.py                             # Main FastAPI application entry point
  │ ├── __init__.py                         # Initialization of the application
  │ ├── commands.py                         # Contains Typer commands to run background processes
  │ ├── routers/                            # FastAPI routers for dividing the app into smaller sub-applications
  │ │ ├── applications.py                   # Router for application endpoints
  │ │ ├── statistics.py                     # Router for statistics endpoints
  │ │ ├── awards.py                         # Router for awards endpoints
  │ │ ├── users.py                          # Router for user endpoints
  │ │ ├── security.py                       # Router for security related endpoints
  │ │ ├── borrowers.py                      # Router for borrower endpoints
  │ │ └── lenders.py                        # Router for lender endpoints
  │ ├── utils/                              # Contains utility functions for the application
  │ │ ├── permissions.py                    # Utility for managing permissions
  │ │ ├── verify_token.py                   # Utility for JWT token verification
  │ │ ├── general_utils.py                  # General utility functions for the app
  │ │ ├── applications.py                   # Utility functions specific to applications
  │ │ ├── email_utility.py                  # Utility for email handling
  │ │ ├── users.py                          # Utility functions specific to users
  │ │ └── lenders.py                        # Utility functions specific to lenders
  │ ├── db/                                 # Handles SQLAlchemy database operations
  │ │ ├── session.py                        # SQLAlchemy session management
  │ ├── core/                               # Contains core settings and configurations
  │ │ ├── email_templates.py                # Email templates for the application
  │ │ ├── settings.py                       # Main settings file for the application, might contain FastAPI and database configurations
  │ │ └── user_dependencies.py              # Manages user dependencies, possibly through FastAPI's dependency injection
  │ ├── background_processes/               # Background tasks for the application
  │ │ ├── application_utils.py              # Utility functions related to applications
  │ │ ├── lapsed_applications.py            # Set applications as lapsed, if the conditions are met, available as a command
  │ │ ├── update_statistic.py               # Updates statistics, available as a command
  │ │ ├── colombia_data_access.py           # Handles data retrieval and processing for contracts, awards, and borrowers.
  │ │ ├── remove_data.py                    # Handles removal of dated application data, available as a command
  │ │ ├── awards_utils.py                   # Utility functions related to awards
  │ │ ├── fetcher.py                        # Fetches new awards, available as a command
  │ │ ├── send_reminder.py                  # Sends reminders mails, available as a command
  │ │ ├── SLA_overdue_applications.py       # Sets overdue applications, available as a command
  │ │ ├── background_utils.py               # General utilities
  │ │ ├── statistics_utils.py               # Utility functions for statistics
  │ │ ├── message_utils.py                  # Utility functions for messaging
  │ │ └── borrower_utils.py                 # Utility functions for borrowers
  │ ├── email_templates/                    # Contains email templates for the application
  │ └── schema/                             # Contains SQLAlchemy schema definitions for the application
  │ ├── diagram                             # Diagram for the schema
  │ ├── statistic.py                        # Statistic schema definition
  │ ├── core.py                             # Core schema definition
  │ ├── api.py                              # API schema definition
  │ └── user_tables/                        # User table schema definition

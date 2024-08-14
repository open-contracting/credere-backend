Cognito
=======

Configuration
-------------

#. Access `Amazon Cognito <https://us-east-1.console.aws.amazon.com/cognito/v2/idp/user-pools?region=us-east-1>`__
#. Click the *Create user pool* button

   Configure sign-in experience
      -  **Cognito user pool sign-in options:** Check "Email"
   Configure security requirements
      -  **Password policy mode:** Check "Custom"
      -  **Password minimum length:** ``14``
      -  **Password requirements:** Uncheck all
      -  **MFA methods:** Check "Authenticator apps"
   Configure sign-up experience
      -  **Self-registration:** Uncheck "Enable self-registration"
   Configure message delivery
      .. tab-set::

         .. tab-item:: Production

            -  **FROM email address:** ``credere@noreply.open-contracting.org``
            -  **FROM sender name:** ``Credere por Open Contracting Partnership <credere@noreply.open-contracting.org>``

         .. tab-item:: Development
      
            -  **Email provider:** Check "Send email with Cognito"
   Integrate your app
      -  **User pool name:** ``credere-production`` for production, ``credere`` for development
      -  **App client name:** ``credere-production`` for production, ``credere`` for development
      -  **Client secret:** Check "Generate a client secret"
      -  **Advanced app client settings:** Check:

         -  ALLOW_REFRESH_TOKEN_AUTH (default)
         -  ALLOW_USER_SRP_AUTH (default)
         -  ALLOW_ADMIN_USER_PASSWORD_AUTH
         -  ALLOW_CUSTOM_AUTH
         -  ALLOW_USER_PASSWORD_AUTH

Tasks
-----

.. _cognito-admin:

Create a first admin user
~~~~~~~~~~~~~~~~~~~~~~~~~

#. Create a user in Cognito:

   #. Access `Amazon Cognito <https://us-east-1.console.aws.amazon.com/cognito/v2/idp/user-pools?region=us-east-1>`__
   #. Click on the user pool's name
   #. Click the *Create user* button

      -  **Invitation message:** Check "Don't send an invitation" (default)
      -  **Email address:** Enter the user's email address
      -  Check "Mark email address as verified"
      -  **Temporary password:** Check "Generate a password"

   #. Copy the user's ID (``sub``), which looks like a UUID

#. Create an ``OCP`` user in the Credere database, for example:

   .. code-block:: none

      INSERT INTO public.credere_user (type, language, email, name, external_id)
      VALUES ('OCP', 'es', 'local@example.com', 'Admin User', '550e8400-e29b-41d4-a716-446655440000');

#. Reset the user's password through the Credere frontend:

   #. Go to the login page
   #. Click *Forgot Password?*
   #. Follow the prompts from the email to set a password and set up MFA

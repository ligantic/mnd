MND
========

About
-----

MND is a patient registry based on TRRF (https://github.com/eresearchqut/trrf).

During development, TRRF is installed as a git submodule.

Refer to the TRRF project for more docs.

Self-registration
-----------------

MND uses its own registration form and processing class, configured in
``mnd/mnd/settings.py``. Patient phone number, country, street, suburb/town and
postcode are mandatory. State/region is optional and is validated against the
selected country. A confirmed MND diagnosis is explained as an eligibility
requirement; the form does not collect a new clinical diagnosis answer.

Registrants may add guardian details. Guardian name, phone and address are
required only when this option is selected; guardian date of birth and gender
are optional. Details are saved in the existing ``ParentGuardian`` model and
linked to the patient without a user account. Patient account ownership and
the separate invitation-based carer access process are unchanged. Authorised
staff can inspect guardian records in the existing administration screen.

The mandatory registration-consent checkbox records the displayed wording,
information-sheet path/version, language, account and acceptance timestamp in
``RegistrationConsent``. Staff with permission can view this read-only record
in administration. It does not populate detailed consent answers, grant
optional research/contact permissions or replace participation consent.
The first-pass wording requires MND review before release. It links to the
approved v2.1 information sheet packaged by the deployment repository.

Apply the new MND and shared patients migrations before enabling this version.
The shared change makes guardian gender optional, including on subsequent
edits; it does not change existing gender values.

Focused validation uses an isolated PostgreSQL container because the shared
models use PostgreSQL array fields. From the ``rdrf/`` directory::

    docker run --rm --name mnd-registration-tests \
      -e POSTGRES_HOST_AUTH_METHOD=trust -p 127.0.0.1::5432 -d postgres:16
    export MND_TEST_DB_PORT=$(docker port mnd-registration-tests 5432/tcp | cut -d: -f2)
    docker exec mnd-registration-tests pg_isready -U postgres
    AWS_XRAY_SDK_ENABLED=false PYTHONPATH="$PWD/rdrf:$PWD/../mnd" DJANGO_SETTINGS_MODULE=mnd.tests.settings \
      .venv/bin/python -m pytest ../mnd/mnd/tests/test_registration.py -q
    docker stop mnd-registration-tests

Wait for ``pg_isready`` to report readiness before running the suite. The test
settings require an explicit local port and use disposable databases, not
configured registry databases. Existing migrations are skipped in the
registration tests; migration-state tests separately check the new operations.

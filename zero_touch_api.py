#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Zero-touch enrollment reseller quickstart.

This script forms the quickstart introduction to the zero-touch enrollemnt
reseller API. To learn more, visit https://developer.google.com/zero-touch
"""

from apiclient import discovery
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from oauth2client import tools
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage



# TODO: replace this with your partner reseller ID.
PARTNER_ID = '1421052759';


# A single auth scope is used for the zero-touch enrollment customer API.
SCOPES = ['https://www.googleapis.com/auth/androidworkprovisioning', 'https://www.googleapis.com/auth/androidworkzerotouchemm']
SERVICE_ACCOUNT_KEY_FILE = 'service_account_key.json'
MACROPAY_JSON = 'macropay.json'

CLIENT_SECRET_FILE = 'client_secret.json'
USER_CREDENTIAL_FILE = 'user_credential.json'

def get_credential_account():
      
  """Creates a Credential object with the correct OAuth2 authorization.

  Creates a Credential object with the correct OAuth2 authorization
  for the service account that calls the reseller API. The service
  endpoint calls this method when setting up a new service instance.

  Returns:
    Credential, the user's credential.
  """
  credential = ServiceAccountCredentials.from_json_keyfile_name(
      SERVICE_ACCOUNT_KEY_FILE, scopes=SCOPES[0])
  
  return credential

def get_credential_customer():
  """Creates a Credential object with the correct OAuth2 authorization.

  Ask the user to authorize the request using their Google Account in their
  browser. Because this method stores the cedential in the
  USER_CREDENTIAL_FILE, the user is typically only asked to the first time they
  run the script.

  Returns:
    Credentials, the user's credential.
  """
  flow = flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES[1])
  storage = Storage(USER_CREDENTIAL_FILE)
  credential = storage.get()

  if not credential or credential.invalid:
    credential = tools.run_flow(flow, storage)  # skipping flags for brevity
  return credential


def get_service(func):
  """Creates a service endpoint for the zero-touch enrollment reseller API.

  Builds and returns an authorized API client service for v1 of the API. Use
  the service endpoint to call the API methods.

  Returns:
    A service Resource object with methods for interacting with the service.
  """
  http_auth = func().authorize(Http())
  service = discovery.build('androiddeviceprovisioning', 'v1', http=http_auth)
  return service

def get_list_of_customers():
    service = get_service(get_credential_account)
    customers = service.partners().customers().list(partnerId=PARTNER_ID).execute()["customers"]
    list_customers = {customer["companyName"]: customer["companyId"] for customer in customers}
    return list_customers
    
    
def claim_device(device_identifier, id_customer):
    service = get_service(get_credential_account)
    claim = build_json_to_claim(device_identifier, id_customer)
    claim_response = service.partners().devices().claim(partnerId = PARTNER_ID, body=claim).execute()
    return claim_response["deviceId"]

def get_configurations(customer_id):
    service_customer = get_service(get_credential_customer)  
    configurations = service_customer.customers().configurations().list(parent = f'customers/{customer_id}').execute()
    configurations_names = [(configuration["name"], configuration["configurationName"]) for configuration in configurations["configurations"]]
    return configurations_names

def set_configuration(configuration, device_id, customer_id):
    service_customer = get_service(get_credential_customer)  
    configuration_json = build_json_to_configuration(configuration, device_id)
    apply_configuration = service_customer.customers().devices().applyConfiguration(parent = f'customers/{customer_id}', body = configuration_json).execute()
    return apply_configuration

def build_json_to_claim(device_identifier, id_customer):
    claim = { # Request message to claim a device on behalf of a customer.
        "customerId": id_customer, # The ID of the customer for whom the device is being claimed.
        "deviceIdentifier": { # Encapsulates hardware and product IDs to identify a manufactured device. To understand requirements on identifier sets, read [Identifiers](https://developers.google.com/zero-touch/guides/identifiers). # Required. Required. The device identifier of the device to claim.
        "imei": device_identifier, # The device’s IMEI number. Validated on input.
            },
        "sectionType": "SECTION_TYPE_ZERO_TOUCH", # Required. The section type of the device's provisioning record.
    }
    return claim
def build_json_to_configuration(configuration_name, claim_device_id ):
    configuration = { # Request message for customer to assign a configuration to device.
        "configuration": configuration_name, # Required. The configuration applied to the device in the format `customers/[CUSTOMER_ID]/configurations/[CONFIGURATION_ID]`.
        "device": { # A `DeviceReference` is an API abstraction that lets you supply a _device_ argument to a method using one of the following identifier types: * A numeric API resource ID. * Real-world hardware IDs, such as IMEI number, belonging to the manufactured device. Methods that operate on devices take a `DeviceReference` as a parameter type because it's more flexible for the caller. To learn more about device identifiers, read [Identifiers](https://developers.google.com/zero-touch/guides/identifiers). # Required. The device the configuration is applied to. There are custom validations in ApplyConfigurationRequestValidator
        "deviceId": claim_device_id, # The ID of the device.
        },
    }
    return configuration
def get_customer_id(customer, list_customers):
    for single_customer in list_customers:
        if customer in single_customer:
            return list_customers[customer]
        
def claim_batch_devices(claims):
    service = get_service(get_credential_account)
    claims = service.partners().devices().claimAsync(partnerId = PARTNER_ID, body = claims).execute()
    return claims
    
def build_bulk_json(id_customer,imeis):
    claims = []
    for imei in imeis:
        claim = { # Request message to claim a device on behalf of a customer.
        "customerId": id_customer, # The ID of the customer for whom the device is being claimed.
        "deviceIdentifier": { # Encapsulates hardware and product IDs to identify a manufactured device. To understand requirements on identifier sets, read [Identifiers](https://developers.google.com/zero-touch/guides/identifiers). # Required. Required. The device identifier of the device to claim.
        "imei": imei, # The device’s IMEI number. Validated on input.
            },
        "sectionType": "SECTION_TYPE_ZERO_TOUCH", # Required. The section type of the device's provisioning record.
        } 
        claims.append(claim)
        
    claim_dict = {
        "claims" : claims
    }
    return claim_dict


def set_default_configuration(configuration_name):
    service_customer = get_service(get_credential_customer)  
    target_configuration = service_customer.customers().configurations().get(name = configuration_name).execute()

    configuration = {
    'isDefault': True,
    'configurationId': target_configuration['configurationId']
    }

    response = service_customer.customers().configurations().patch(
    name=target_configuration['name'],
    body=configuration, updateMask='isDefault').execute()
    return response

def unclaim_single_device(imei):
    service = get_service(get_credential_account)
    unclaim_json = { # Request message to unclaim a device.
    "deviceIdentifier": { # Encapsulates hardware and product IDs to identify a manufactured device. To understand requirements on identifier sets, read [Identifiers](https://developers.google.com/zero-touch/guides/identifiers). # Required. The device identifier you used when you claimed this device.
        "imei": imei, # The device’s IMEI number. Validated on input.
        },
    "sectionType": "SECTION_TYPE_ZERO_TOUCH", # Required. The section type of the device's provisioning record.
    }
    unclaim = service.partners().devices().unclaim(partnerId = PARTNER_ID, body = unclaim_json).execute()
    return unclaim
 
    
def get_device_information(imei):    
    service = get_service(get_credential_account)
    device_info = { # Request to find devices.
        "deviceIdentifier": { # Encapsulates hardware and product IDs to identify a manufactured device. To understand requirements on identifier sets, read [Identifiers](https://developers.google.com/zero-touch/guides/identifiers). # Required. Required. The device identifier to search for.
            "imei": imei, # The device’s IMEI number. Validated on input.
            },
        "limit": "1", # Required. The maximum number of devices to show in a page of results. Must be between 1 and 100 inclusive.
    }
    get_device = service.partners().devices().findByIdentifier(partnerId = PARTNER_ID, body = device_info).execute()
    return get_device["devices"][0]["deviceId"]

def build_bulk_unclaim_json(imeis):
    unclaims = []
    for imei in imeis:
        
        unclaim = { # Request message to claim a device on behalf of a customer.
        "deviceIdentifier": { # Encapsulates hardware and product IDs to identify a manufactured device. To understand requirements on identifier sets, read [Identifiers](https://developers.google.com/zero-touch/guides/identifiers). # Required. Required. The device identifier of the device to claim.
            "imei": imei, # The device’s IMEI number. Validated on input.
            },
        "sectionType": "SECTION_TYPE_ZERO_TOUCH", # Required. The section type of the device's provisioning record.
        } 
        unclaims.append(unclaim)
    unclaim_dict ={
        "unclaims": unclaims
    }
        
    return unclaim_dict

def unclaim_batch_devices(unclaims):
    service = get_service(get_credential_account)
    unclaims_response = service.partners().devices().unclaimAsync(partnerId = PARTNER_ID, body = unclaims).execute()
    return unclaims_response
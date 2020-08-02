from __future__ import absolute_import, division, print_function

__metaclass__ = type
import socket
import json

DOCUMENTATION = """
module: vcenter_vm_hardware_cpu
short_description: Handle resource of type vcenter_vm_hardware_cpu
description: Handle resource of type vcenter_vm_hardware_cpu
options:
  cores_per_socket:
    description:
    - New number of CPU cores per socket. The number of CPU cores in the virtual machine
      must be a multiple of the number of cores per socket.
    - If unset, the value is unchanged.
    type: int
  count:
    description:
    - 'New number of CPU cores. The number of CPU cores in the virtual machine must
      be a multiple of the number of cores per socket. '
    - ' The supported range of CPU counts is constrained by the configured guest operating
      system and virtual hardware version of the virtual machine. '
    - ' If the virtual machine is running, the number of CPU cores may only be increased
      if Cpu.Info.hot-add-enabled is true, and may only be decreased if Cpu.Info.hot-remove-enabled
      is true.'
    - If unset, the value is unchanged.
    type: int
  hot_add_enabled:
    description:
    - 'Flag indicating whether adding CPUs while the virtual machine is running is
      enabled. '
    - ' This field may only be modified if the virtual machine is powered off.'
    - If unset, the value is unchanged.
    type: bool
  hot_remove_enabled:
    description:
    - 'Flag indicating whether removing CPUs while the virtual machine is running
      is enabled. '
    - ' This field may only be modified if the virtual machine is powered off.'
    - If unset, the value is unchanged.
    type: bool
  state:
    choices:
    - update
    description: []
    type: str
  vm:
    description:
    - Virtual machine identifier.
    - 'The parameter must be an identifier for the resource type: VirtualMachine.'
    type: str
author:
- Ansible VMware team
version_added: 1.0.0
requirements:
- python >= 3.6
"""
IN_QUERY_PARAMETER = []
from ansible.module_utils.basic import env_fallback

try:
    from ansible_module.turbo.module import AnsibleTurboModule as AnsibleModule
except ImportError:
    from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vmware.vmware_rest.plugins.module_utils.vmware_rest import (
    gen_args,
    open_session,
    update_changed_flag,
)


def prepare_argument_spec():
    argument_spec = {
        "vcenter_hostname": dict(
            type="str", required=False, fallback=(env_fallback, ["VMWARE_HOST"])
        ),
        "vcenter_username": dict(
            type="str", required=False, fallback=(env_fallback, ["VMWARE_USER"])
        ),
        "vcenter_password": dict(
            type="str",
            required=False,
            no_log=True,
            fallback=(env_fallback, ["VMWARE_PASSWORD"]),
        ),
        "vcenter_certs": dict(
            type="bool",
            required=False,
            no_log=True,
            fallback=(env_fallback, ["VMWARE_VALIDATE_CERTS"]),
        ),
    }
    argument_spec["vm"] = {"type": "str", "operationIds": ["update"]}
    argument_spec["state"] = {"type": "str", "choices": ["update"]}
    argument_spec["hot_remove_enabled"] = {"type": "bool", "operationIds": ["update"]}
    argument_spec["hot_add_enabled"] = {"type": "bool", "operationIds": ["update"]}
    argument_spec["count"] = {"type": "int", "operationIds": ["update"]}
    argument_spec["cores_per_socket"] = {"type": "int", "operationIds": ["update"]}
    return argument_spec


async def get_device_info(params, session, _url, _key):
    async with session.get(((_url + "/") + _key)) as resp:
        _json = await resp.json()
        entry = _json["value"]
        entry["_key"] = _key
        return entry


async def list_devices(params, session):
    existing_entries = []
    _url = url(params)
    async with session.get(_url) as resp:
        _json = await resp.json()
        devices = _json["value"]
    for device in devices:
        _id = list(device.values())[0]
        existing_entries.append((await get_device_info(params, session, _url, _id)))
    return existing_entries


async def exists(params, session):
    unicity_keys = ["bus", "pci_slot_number"]
    devices = await list_devices(params, session)
    for device in devices:
        for k in unicity_keys:
            if (params.get(k) is not None) and (device.get(k) != params.get(k)):
                break
        else:
            return device


async def main():
    module_args = prepare_argument_spec()
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)
    session = await open_session(
        vcenter_hostname=module.params["vcenter_hostname"],
        vcenter_username=module.params["vcenter_username"],
        vcenter_password=module.params["vcenter_password"],
    )
    result = await entry_point(module, session)
    module.exit_json(**result)


def url(params):
    return "https://{vcenter_hostname}/rest/vcenter/vm/{vm}/hardware/cpu".format(
        **params
    )


async def entry_point(module, session):
    func = globals()[("_" + module.params["state"])]
    return await func(module.params, session)


async def _update(params, session):
    accepted_fields = [
        "cores_per_socket",
        "count",
        "hot_add_enabled",
        "hot_remove_enabled",
    ]
    if "update" == "create":
        _exists = await exists(params, session)
        if _exists:
            return await update_changed_flag({"value": _exists}, 200, "get")
    spec = {}
    for i in accepted_fields:
        if params[i]:
            spec[i] = params[i]
    _url = "https://{vcenter_hostname}/rest/vcenter/vm/{vm}/hardware/cpu".format(
        **params
    )
    async with session.patch(_url, json={"spec": spec}) as resp:
        try:
            if resp.headers["Content-Type"] == "application/json":
                _json = await resp.json()
        except KeyError:
            _json = {}
        if (
            ("update" == "create")
            and (resp.status in [200, 201])
            and ("value" in _json)
        ):
            if type(_json["value"]) == dict:
                _id = list(_json["value"].values())[0]
            else:
                _id = _json["value"]
            _json = {"value": (await get_device_info(params, session, _url, _id))}
        return await update_changed_flag(_json, resp.status, "update")


if __name__ == "__main__":
    import asyncio

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

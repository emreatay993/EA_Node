from __future__ import annotations

import json

import pytest

from ea_node_editor.nodes.builtins import integrations_ssh_sftp as ssh_sftp
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.plugin_contracts import PluginContractManifest
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.runtime_contracts import (
    DataTypeCatalogError,
    deserialize_runtime_value,
    serialize_runtime_value,
)


NODE_METADATA = {
    "ssh_sftp.secret": (
        "Secret",
        "Store strings securely as secrets using Windows Data Protection API. "
        "Decryption can be limited to the current user or all users on this machine.",
        ("Secure", "Encrypted", "Password", "Credentials"),
    ),
    "ssh_sftp.host": (
        "SSH/SFTP Host",
        "Representing a SSH Host to be used with the SSH/SFTP/SCP-Command nodes.",
        ("FTP", "SCP", "Linux", "Unix", "Authentication", "Upload", "Download", "HPC"),
    ),
    "ssh_sftp.run_command": (
        "Run SSH Command",
        "Run commands via SSH on a remote host.",
        ("Linux", "Unix", "Execute", "Remote", "Shell", "Bash", "HPC"),
    ),
    "ssh_sftp.run_script": (
        "Run SSH Script",
        "Run a script via SSH on a remote host.",
        ("Linux", "Unix", "Commands", "Execute", "Remote", "Shell", "Bash", "sh", "HPC"),
    ),
    "ssh_sftp.upload": (
        "SFTP Upload",
        "Upload files or directories to a remote machine via SFTP.",
        ("Linux", "Unix", "SSH", "FTP", "SCP", "Put", "HPC", "Transfer"),
    ),
    "ssh_sftp.download": (
        "SFTP Download",
        "Download files or directories from a remote machine via SFTP.",
        ("Linux", "Unix", "SSH", "FTP", "SCP", "Get", "HPC", "Transfer"),
    ),
}

PORT_CONTRACTS = {
    "ssh_sftp.secret": (
        (
            "secret_value",
            "Secret value",
            "out",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData',
            "item",
            None,
            False,
            (),
            "Holds the encrypted value in a SecretData type.",
        ),
    ),
    "ssh_sftp.host": (
        ("address", "Address", "in", 'COREX.DataTypes.String', "item", True, False, (), "Hostname or IP address of the host."),
        ("port", "Port", "in", 'COREX.DataTypes.Int', "item", False, True, (), "Port for SSH, defaults to 22."),
        (
            "username",
            "Username",
            "in",
            'COREX.DataTypes.String',
            "item",
            True,
            False,
            (),
            "Username of the user you want to authenticate with.",
        ),
        (
            "password",
            "Password",
            "in",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData',
            "item",
            False,
            False,
            (),
            'Optional password, SSH keys are preferred. It is recommended to use the "Secret" node '
            "to pass in the password.",
        ),
        (
            "private_key_path",
            "Private key path",
            "in",
            'COREX.DataTypes.String',
            "item",
            False,
            False,
            ('COREX.DataTypes.String', 'COREX.DataTypes.Path'),
            "Path to SSH private key file.",
        ),
        (
            "private_key_passphrase",
            "Private key passphrase",
            "in",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData',
            "item",
            False,
            False,
            (),
            'Optional passphrase, if the private key is encrypted. It is recommended to use the "Secret" '
            "node to pass in the passphrase.",
        ),
        (
            "use_openssh_agent",
            "Use OpenSSH Agent",
            "in",
            'COREX.DataTypes.Bool',
            "item",
            False,
            True,
            (),
            "If enabled, tries to authenticate using keys from the OpenSSH agent (ssh-agent).",
        ),
        (
            "use_pageant",
            "Use Pageant",
            "in",
            'COREX.DataTypes.Bool',
            "item",
            False,
            True,
            (),
            "If enabled, tries to authenticate using keys from PuTTY's Pageant agent.",
        ),
        (
            "host",
            "SSH/SFTP Host",
            "out",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            "item",
            None,
            False,
            (),
            "SSH/SFTP Host for use in related SSH/SFTP nodes.",
        ),
    ),
    "ssh_sftp.run_command": (
        (
            "target_host",
            "Target Host",
            "in",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            "item",
            True,
            False,
            (),
            "Target host to run command on.",
        ),
        (
            "command",
            "Command",
            "in",
            'COREX.DataTypes.String',
            "item",
            True,
            False,
            (),
            "Run a command on the target remote machine via SSH.",
        ),
        (
            "successful",
            "Successful",
            "out",
            'COREX.DataTypes.Bool',
            "item",
            None,
            False,
            (),
            "'True' if the command exited with exit code 0.",
        ),
        (
            "exit_code",
            "Exit code",
            "out",
            'COREX.DataTypes.Int',
            "item",
            None,
            False,
            (),
            "Exit or return code of the remote shell.",
        ),
        (
            "output",
            "Output",
            "out",
            'COREX.DataTypes.String',
            "item",
            None,
            False,
            (),
            "Text output from the command to the shell is delivered to the stdout (standard out) stream",
        ),
        (
            "error",
            "Error",
            "out",
            'COREX.DataTypes.String',
            "item",
            None,
            False,
            (),
            "Error messages from the command are sent to the stderr (standard error) stream.",
        ),
    ),
    "ssh_sftp.run_script": (
        (
            "target_host",
            "Target Host",
            "in",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            "item",
            True,
            False,
            (),
            "Target host to run command on.",
        ),
        (
            "script",
            "Script",
            "in",
            'COREX.DataTypes.String',
            "item",
            True,
            False,
            (),
            "The script to execute. This could be either a script as plain text or a file path to a script "
            "on the machine executing the workflow.",
        ),
        (
            "successful",
            "Successful",
            "out",
            'COREX.DataTypes.Bool',
            "item",
            None,
            False,
            (),
            "'True' if the script exited with exit code 0.",
        ),
        (
            "exit_code",
            "Exit code",
            "out",
            'COREX.DataTypes.Int',
            "item",
            None,
            False,
            (),
            "Exit or return code of the remote shell.",
        ),
        (
            "output",
            "Output",
            "out",
            'COREX.DataTypes.String',
            "item",
            None,
            False,
            (),
            "Text output from the script to the shell is delivered to the stdout (standard out) stream",
        ),
        (
            "error",
            "Error",
            "out",
            'COREX.DataTypes.String',
            "item",
            None,
            False,
            (),
            "Error messages from the script are sent to the stderr (standard error) stream.",
        ),
    ),
    "ssh_sftp.upload": (
        (
            "target_host",
            "Target Host",
            "in",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            "item",
            True,
            False,
            (),
            "Target SSH/SFTP Host to upload to.",
        ),
        (
            "sources",
            "Sources",
            "in",
            'COREX.DataTypes.String',
            "list",
            True,
            False,
            (),
            "Source files or directories to upload.",
        ),
        (
            "destination",
            "Destination",
            "in",
            'COREX.DataTypes.String',
            "item",
            True,
            False,
            (),
            "Destination file or directory to upload to. You can use . as the destination to upload to the "
            "home directory of the user.",
        ),
        (
            "overwrite",
            "Overwrite existing files",
            "in",
            'COREX.DataTypes.Bool',
            "item",
            False,
            True,
            (),
            "Allow overwriting if the source files already exists in the destination.",
        ),
        (
            "successful",
            "Successful",
            "out",
            'COREX.DataTypes.Bool',
            "item",
            None,
            False,
            (),
            "'True' if the upload was successful.",
        ),
        (
            "uploaded_bytes",
            "Uploaded bytes",
            "out",
            'COREX.DataTypes.Int',
            "item",
            None,
            False,
            (),
            "Amount of bytes uploaded.",
        ),
        (
            "uploaded_files",
            "Uploaded files",
            "out",
            'COREX.DataTypes.Int',
            "item",
            None,
            False,
            (),
            "Amount of files uploaded.",
        ),
    ),
    "ssh_sftp.download": (
        (
            "target_host",
            "Target Host",
            "in",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            "item",
            True,
            False,
            (),
            "Target SSH/SFTP Host to download from.",
        ),
        (
            "sources",
            "Sources",
            "in",
            'COREX.DataTypes.String',
            "list",
            True,
            False,
            (),
            "Source files or directories to download.",
        ),
        (
            "destination",
            "Destination",
            "in",
            'COREX.DataTypes.String',
            "item",
            True,
            False,
            (),
            "Destination file or directory to download to. You can use . as the destination to download to "
            "the current working directory.",
        ),
        (
            "overwrite",
            "Overwrite existing files",
            "in",
            'COREX.DataTypes.Bool',
            "item",
            False,
            True,
            (),
            "Allow overwriting if the source already exists in the destination.",
        ),
        (
            "successful",
            "Successful",
            "out",
            'COREX.DataTypes.Bool',
            "item",
            None,
            False,
            (),
            "'True' if the download was successful.",
        ),
        (
            "downloaded_bytes",
            "Downloaded bytes",
            "out",
            'COREX.DataTypes.Int',
            "item",
            None,
            False,
            (),
            "Amount of bytes Downloaded.",
        ),
        (
            "downloaded_files",
            "Downloaded files",
            "out",
            'COREX.DataTypes.Int',
            "item",
            None,
            False,
            (),
            "Amount of files Downloaded.",
        ),
    ),
}


def _specs():
    return tuple(descriptor.spec for descriptor in ssh_sftp.SSH_SFTP_NODE_DESCRIPTORS)


def test_ssh_sftp_node_metadata_and_catalogue_port_contracts() -> None:
    specs = _specs()

    assert tuple(spec.type_id for spec in specs) == tuple(NODE_METADATA)
    for spec in specs:
        display_name, description, keywords = NODE_METADATA[spec.type_id]
        assert (spec.display_name, spec.category_path) == (display_name, ("Control", "SSH/SFTP"))
        assert spec.description == description
        assert spec.keywords == keywords
        assert spec.dynamic_port_groups == ()
        assert spec.settings_groups == ()
        assert all(port.kind == "data" and port.exposed for port in spec.ports)
        assert tuple(
            (
                port.key,
                port.label,
                port.direction,
                port.data_type,
                port.data_access,
                port.required,
                port.uses_property_default,
                port.accepted_data_types,
                port.description,
            )
            for port in spec.ports
        ) == PORT_CONTRACTS[spec.type_id]


def test_ssh_sftp_properties_and_typed_credential_boundaries() -> None:
    specs = {spec.type_id: spec for spec in _specs()}

    secret_properties = {prop.key: prop for prop in specs["ssh_sftp.secret"].properties}
    value = secret_properties["protected_value"]
    assert (value.type, value.default, value.label) == ("json", {}, "Value")
    assert (value.inline_editor, value.inspector_editor) == ("secret", "secret")
    assert value.sensitive is True
    assert value.sensitive_scope_key == "data_protection_scope"
    scope = secret_properties["data_protection_scope"]
    assert (scope.type, scope.default, scope.label) == (
        "enum",
        "Current user",
        "Data Protection Scope",
    )
    assert scope.enum_values == ("Current user", "All users on this machine")
    assert (scope.inline_editor, scope.inspector_editor) == ("enum", "enum")

    host = specs["ssh_sftp.host"]
    host_properties = {prop.key: prop for prop in host.properties}
    assert (host_properties["port"].type, host_properties["port"].default) == ("int", 22)
    assert host_properties["use_openssh_agent"].default is False
    assert host_properties["use_pageant"].default is False
    host_ports = {port.key: port for port in host.ports}
    assert host_ports["password"].data_type == ssh_sftp.SSH_SFTP_SECRET_DATA_TYPE_ID
    assert host_ports["password"].accepted_data_types == ()
    assert (
        host_ports["private_key_passphrase"].data_type
        == ssh_sftp.SSH_SFTP_SECRET_DATA_TYPE_ID
    )
    assert host_ports["private_key_passphrase"].accepted_data_types == ()
    assert host_ports["private_key_path"].data_type == "COREX.DataTypes.String"
    assert host_ports["private_key_path"].accepted_data_types == (
        "COREX.DataTypes.String",
        "COREX.DataTypes.Path",
    )

    script_property = specs["ssh_sftp.run_script"].properties[0]
    assert (script_property.key, script_property.type, script_property.default) == (
        "interpreter",
        "enum",
        "Bash",
    )
    assert script_property.enum_values == ("Bash", "sh", "Python 3", "Python 2", "Perl", "Custom")
    assert tuple(prop.key for prop in specs["ssh_sftp.run_script"].properties) == ("interpreter",)

    for type_id in ("ssh_sftp.upload", "ssh_sftp.download"):
        overwrite = specs[type_id].properties
        assert len(overwrite) == 1
        assert (overwrite[0].key, overwrite[0].type, overwrite[0].default) == (
            "overwrite",
            "bool",
            False,
        )


def test_ssh_sftp_descriptors_validate_and_have_complete_authored_help() -> None:
    registry = NodeRegistry()
    registry.register_plugin_bundle(
        PluginContractManifest(
            data_type_families=ssh_sftp.SSH_SFTP_DATA_TYPE_FAMILIES,
            data_types=ssh_sftp.SSH_SFTP_DATA_TYPES,
        ),
        ssh_sftp.SSH_SFTP_NODE_DESCRIPTORS,
        owner_id=ssh_sftp.SSH_SFTP_DATA_TYPE_OWNER_ID,
    )

    specs = _specs()
    assert all(spec.description.strip() and spec.keywords for spec in specs)
    assert all(port.description.strip() for spec in specs for port in spec.ports)


def test_ssh_sftp_runtime_type_contracts_and_process_transport_are_exact() -> None:
    registry = NodeRegistry()
    registry.register_plugin_bundle(
        PluginContractManifest(
            data_type_families=ssh_sftp.SSH_SFTP_DATA_TYPE_FAMILIES,
            data_types=ssh_sftp.SSH_SFTP_DATA_TYPES,
        ),
        ssh_sftp.SSH_SFTP_NODE_DESCRIPTORS,
        owner_id=ssh_sftp.SSH_SFTP_DATA_TYPE_OWNER_ID,
    )

    secret_type_id = "SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData"
    host_type_id = "SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData"
    expected_specs = {
        secret_type_id: ("Secret", "secret"),
        host_type_id: ("SSH/SFTP Host", "sensitive"),
    }
    for type_id, (display_name, sensitivity) in expected_specs.items():
        spec = registry.data_types.require(type_id)
        assert (
            spec.display_name,
            spec.family_id,
            spec.parents,
            spec.abstract,
            spec.carriers,
            spec.persistence,
            spec.sensitivity,
            registry.data_types.owner_of(type_id),
        ) == (
            display_name,
            "ssh_sftp",
            ("COREX.DataTypes.Any",),
            False,
            frozenset({"native"}),
            "never",
            sensitivity,
            "corex.ssh_sftp",
        )

    protected_envelope = {
        "schema": "corex.protected_secret.v1",
        "provider": "windows_dpapi",
        "scope": "CurrentUser",
        "ciphertext_b64": "AA==",
    }
    secret = ssh_sftp.compute_secret(
        ExecutionContext(
            run_id="run",
            node_id="node",
            workspace_id="workspace",
            inputs={},
            properties={"protected_value": protected_envelope},
            emit_log=lambda *_args: None,
        )
    ).outputs["secret_value"]
    assert secret == {
        "__ea_runtime_value__": "secret_data",
        "revision": 1,
        "provider": "windows_dpapi",
        "scope": "CurrentUser",
        "ciphertext_b64": "AA==",
    }

    host = ssh_sftp.compute_host(
        ExecutionContext(
            run_id="run",
            node_id="node",
            workspace_id="workspace",
            inputs={"address": "host", "username": "user", "password": secret},
            properties={},
            emit_log=lambda *_args: None,
        )
    ).outputs["host"]
    assert host == {
        "__ea_runtime_value__": "ssh_sftp_host_data",
        "revision": 1,
        "address": "host",
        "port": 22,
        "username": "user",
        "password": secret,
        "private_key_path": "",
        "private_key_passphrase": None,
        "use_openssh_agent": False,
        "use_pageant": False,
    }

    registry.data_types.validate_carrier(secret_type_id, secret)
    registry.data_types.validate_carrier(host_type_id, host)

    for bad_secret in (
        secret | {"__ea_runtime_value__": "bad_secret_data"},
        secret | {"revision": 2},
        secret | {"provider": "bad_provider"},
    ):
        with pytest.raises(DataTypeCatalogError):
            registry.data_types.validate_carrier(secret_type_id, bad_secret)
    for bad_host in (
        host | {"__ea_runtime_value__": "bad_host_data"},
        host | {"revision": 2},
        host | {"password": None},
    ):
        with pytest.raises(DataTypeCatalogError):
            registry.data_types.validate_carrier(host_type_id, bad_host)

    for type_id, value in ((secret_type_id, secret), (host_type_id, host)):
        wire = serialize_runtime_value(
            value,
            catalog=registry.data_types,
            declared_type_id=type_id,
        )
        wire = json.loads(json.dumps(wire))
        restored = deserialize_runtime_value(
            wire,
            catalog=registry.data_types,
            declared_type_id=type_id,
        )
        assert restored == value


@pytest.mark.parametrize(
    ("type_id", "callback_name"),
    (
        ("ssh_sftp.secret", "compute_secret"),
        ("ssh_sftp.host", "compute_host"),
        ("ssh_sftp.run_command", "run_ssh_command"),
        ("ssh_sftp.run_script", "run_ssh_script"),
        ("ssh_sftp.upload", "sftp_upload"),
        ("ssh_sftp.download", "sftp_download"),
    ),
)
def test_ssh_sftp_plugin_execute_delegates_to_runtime_callback(
    monkeypatch: pytest.MonkeyPatch,
    type_id: str,
    callback_name: str,
) -> None:
    descriptor = next(
        descriptor
        for descriptor in ssh_sftp.SSH_SFTP_NODE_DESCRIPTORS
        if descriptor.spec.type_id == type_id
    )
    context = object()
    expected = NodeResult(outputs={"sentinel": callback_name})
    seen = []

    def callback(ctx):
        seen.append(ctx)
        return expected

    monkeypatch.setattr(ssh_sftp, callback_name, callback)

    assert descriptor.factory().execute(context) is expected
    assert seen == [context]

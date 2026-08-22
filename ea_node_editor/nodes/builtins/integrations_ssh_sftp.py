# Purpose: Declare the built-in SSH/SFTP connector nodes and delegate their execution.
# Map: feature_routes/ssh_sftp_nodes.md
# Tests: tests/test_ssh_sftp_node_contracts.py

from __future__ import annotations

from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type
from ea_node_editor.nodes.builtins.ssh_sftp_runtime import (
    _coerce_host,
    _coerce_secret,
    compute_host,
    compute_secret,
    run_ssh_command,
    run_ssh_script,
    sftp_download,
    sftp_upload,
)
from ea_node_editor.nodes.core_data_types import GRAPH_DATA_TYPE_ID
from ea_node_editor.nodes.decorators import plugin_descriptor
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import PortSpec, PropertySpec
from ea_node_editor.runtime_contracts import DataTypeFamilySpec, DataTypeSpec

SSH_SFTP_CATEGORY = ("Control", "SSH/SFTP")
DATA_PROTECTION_SCOPES = ("Current user", "All users on this machine")
SCRIPT_INTERPRETERS = ("Bash", "sh", "Python 3", "Python 2", "Perl", "Custom")
SSH_SFTP_HOST_DATA_TYPE_ID = (
    "SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData"
)
SSH_SFTP_SECRET_DATA_TYPE_ID = "SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData"
SSH_SFTP_DATA_TYPE_OWNER_ID = "corex.ssh_sftp"


def _is_secret_data(value: object) -> bool:
    try:
        return _coerce_secret(value, input_name="Secret") is not None
    except (TypeError, ValueError):
        return False


def _is_host_data(value: object) -> bool:
    try:
        _coerce_host(value)
    except (TypeError, ValueError):
        return False
    return True


SSH_SFTP_DATA_TYPE_FAMILIES = (
    DataTypeFamilySpec("ssh_sftp", "SSH/SFTP", "data.integration", "network"),
)
SSH_SFTP_DATA_TYPES = (
    DataTypeSpec(
        SSH_SFTP_SECRET_DATA_TYPE_ID,
        "Secret",
        "ssh_sftp",
        _is_secret_data,
        parents=(GRAPH_DATA_TYPE_ID,),
        persistence="never",
        sensitivity="secret",
    ),
    DataTypeSpec(
        SSH_SFTP_HOST_DATA_TYPE_ID,
        "SSH/SFTP Host",
        "ssh_sftp",
        _is_host_data,
        parents=(GRAPH_DATA_TYPE_ID,),
        persistence="never",
        sensitivity="sensitive",
    ),
)


@builtin_node_type(
    type_id="ssh_sftp.secret",
    display_name="Secret",
    category_path=SSH_SFTP_CATEGORY,
    description=(
        "Store strings securely as secrets using Windows Data Protection API. "
        "Decryption can be limited to the current user or all users on this machine."
    ),
    keywords=("Secure", "Encrypted", "Password", "Credentials"),
    ports=(
        PortSpec(
            "secret_value",
            "out",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData',
            label="Secret value",
            description="Holds the encrypted value in a SecretData type.",
        ),
    ),
    properties=(
        PropertySpec(
            "protected_value",
            "json",
            {},
            "Value",
            inline_editor="secret",
            inspector_editor="secret",
            description="Write-only secret value protected by Windows Data Protection API.",
            sensitive=True,
            sensitive_scope_key="data_protection_scope",
        ),
        PropertySpec(
            "data_protection_scope",
            "enum",
            "Current user",
            "Data Protection Scope",
            enum_values=DATA_PROTECTION_SCOPES,
            inline_editor="enum",
            inspector_editor="enum",
            description="Choose who on this Windows machine can decrypt the secret.",
        ),
    ),
)
class SecretNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return compute_secret(ctx)


@builtin_node_type(
    type_id="ssh_sftp.host",
    display_name="SSH/SFTP Host",
    category_path=SSH_SFTP_CATEGORY,
    description="Representing a SSH Host to be used with the SSH/SFTP/SCP-Command nodes.",
    keywords=(
        "FTP",
        "SCP",
        "Linux",
        "Unix",
        "Authentication",
        "Upload",
        "Download",
        "HPC",
    ),
    ports=(
        PortSpec(
            "address",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Address",
            required=True,
            description="Hostname or IP address of the host.",
        ),
        PortSpec(
            "port",
            "in",
            "data",
            'COREX.DataTypes.Int',
            label="Port",
            required=False,
            uses_property_default=True,
            description="Port for SSH, defaults to 22.",
        ),
        PortSpec(
            "username",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Username",
            required=True,
            description="Username of the user you want to authenticate with.",
        ),
        PortSpec(
            "password",
            "in",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData',
            label="Password",
            required=False,
            description=(
                'Optional password, SSH keys are preferred. It is recommended to use the '
                '"Secret" node to pass in the password.'
            ),
        ),
        PortSpec(
            "private_key_path",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Private key path",
            required=False,
            accepted_data_types=('COREX.DataTypes.String', 'COREX.DataTypes.Path'),
            description="Path to SSH private key file.",
        ),
        PortSpec(
            "private_key_passphrase",
            "in",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SecretData',
            label="Private key passphrase",
            required=False,
            description=(
                'Optional passphrase, if the private key is encrypted. It is recommended '
                'to use the "Secret" node to pass in the passphrase.'
            ),
        ),
        PortSpec(
            "use_openssh_agent",
            "in",
            "data",
            'COREX.DataTypes.Bool',
            label="Use OpenSSH Agent",
            required=False,
            uses_property_default=True,
            description=(
                "If enabled, tries to authenticate using keys from the OpenSSH agent "
                "(ssh-agent)."
            ),
        ),
        PortSpec(
            "use_pageant",
            "in",
            "data",
            'COREX.DataTypes.Bool',
            label="Use Pageant",
            required=False,
            uses_property_default=True,
            description="If enabled, tries to authenticate using keys from PuTTY's Pageant agent.",
        ),
        PortSpec(
            "host",
            "out",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            label="SSH/SFTP Host",
            description="SSH/SFTP Host for use in related SSH/SFTP nodes.",
        ),
    ),
    properties=(
        PropertySpec("port", "int", 22, "Port"),
        PropertySpec("use_openssh_agent", "bool", False, "Use OpenSSH Agent"),
        PropertySpec("use_pageant", "bool", False, "Use Pageant"),
    ),
)
class SshSftpHostNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return compute_host(ctx)


@builtin_node_type(
    type_id="ssh_sftp.run_command",
    display_name="Run SSH Command",
    category_path=SSH_SFTP_CATEGORY,
    description="Run commands via SSH on a remote host.",
    keywords=("Linux", "Unix", "Execute", "Remote", "Shell", "Bash", "HPC"),
    ports=(
        PortSpec(
            "target_host",
            "in",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            label="Target Host",
            required=True,
            description="Target host to run command on.",
        ),
        PortSpec(
            "command",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Command",
            required=True,
            description="Run a command on the target remote machine via SSH.",
        ),
        PortSpec(
            "successful",
            "out",
            "data",
            'COREX.DataTypes.Bool',
            label="Successful",
            description="'True' if the command exited with exit code 0.",
        ),
        PortSpec(
            "exit_code",
            "out",
            "data",
            'COREX.DataTypes.Int',
            label="Exit code",
            description="Exit or return code of the remote shell.",
        ),
        PortSpec(
            "output",
            "out",
            "data",
            'COREX.DataTypes.String',
            label="Output",
            description=(
                "Text output from the command to the shell is delivered to the stdout "
                "(standard out) stream"
            ),
        ),
        PortSpec(
            "error",
            "out",
            "data",
            'COREX.DataTypes.String',
            label="Error",
            description=(
                "Error messages from the command are sent to the stderr (standard error) stream."
            ),
        ),
    ),
    properties=(),
)
class RunSshCommandNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return run_ssh_command(ctx)


@builtin_node_type(
    type_id="ssh_sftp.run_script",
    display_name="Run SSH Script",
    category_path=SSH_SFTP_CATEGORY,
    description="Run a script via SSH on a remote host.",
    keywords=("Linux", "Unix", "Commands", "Execute", "Remote", "Shell", "Bash", "sh", "HPC"),
    ports=(
        PortSpec(
            "target_host",
            "in",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            label="Target Host",
            required=True,
            description="Target host to run command on.",
        ),
        PortSpec(
            "script",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Script",
            required=True,
            description=(
                "The script to execute. This could be either a script as plain text or a "
                "file path to a script on the machine executing the workflow."
            ),
        ),
        PortSpec(
            "successful",
            "out",
            "data",
            'COREX.DataTypes.Bool',
            label="Successful",
            description="'True' if the script exited with exit code 0.",
        ),
        PortSpec(
            "exit_code",
            "out",
            "data",
            'COREX.DataTypes.Int',
            label="Exit code",
            description="Exit or return code of the remote shell.",
        ),
        PortSpec(
            "output",
            "out",
            "data",
            'COREX.DataTypes.String',
            label="Output",
            description=(
                "Text output from the script to the shell is delivered to the stdout "
                "(standard out) stream"
            ),
        ),
        PortSpec(
            "error",
            "out",
            "data",
            'COREX.DataTypes.String',
            label="Error",
            description=(
                "Error messages from the script are sent to the stderr (standard error) stream."
            ),
        ),
    ),
    properties=(
        PropertySpec(
            "interpreter",
            "enum",
            "Bash",
            "Interpreter",
            enum_values=SCRIPT_INTERPRETERS,
            inspector_editor="enum",
            description=(
                "Interpreter available on the target host; Custom uses the script shebang."
            ),
        ),
    ),
)
class RunSshScriptNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return run_ssh_script(ctx)


@builtin_node_type(
    type_id="ssh_sftp.upload",
    display_name="SFTP Upload",
    category_path=SSH_SFTP_CATEGORY,
    description="Upload files or directories to a remote machine via SFTP.",
    keywords=("Linux", "Unix", "SSH", "FTP", "SCP", "Put", "HPC", "Transfer"),
    ports=(
        PortSpec(
            "target_host",
            "in",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            label="Target Host",
            required=True,
            description="Target SSH/SFTP Host to upload to.",
        ),
        PortSpec(
            "sources",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Sources",
            required=True,
            data_access="list",
            description="Source files or directories to upload.",
        ),
        PortSpec(
            "destination",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Destination",
            required=True,
            description=(
                "Destination file or directory to upload to. You can use . as the "
                "destination to upload to the home directory of the user."
            ),
        ),
        PortSpec(
            "overwrite",
            "in",
            "data",
            'COREX.DataTypes.Bool',
            label="Overwrite existing files",
            required=False,
            uses_property_default=True,
            description=(
                "Allow overwriting if the source files already exists in the destination."
            ),
        ),
        PortSpec(
            "successful",
            "out",
            "data",
            'COREX.DataTypes.Bool',
            label="Successful",
            description="'True' if the upload was successful.",
        ),
        PortSpec(
            "uploaded_bytes",
            "out",
            "data",
            'COREX.DataTypes.Int',
            label="Uploaded bytes",
            description="Amount of bytes uploaded.",
        ),
        PortSpec(
            "uploaded_files",
            "out",
            "data",
            'COREX.DataTypes.Int',
            label="Uploaded files",
            description="Amount of files uploaded.",
        ),
    ),
    properties=(PropertySpec("overwrite", "bool", False, "Overwrite existing files"),),
)
class SftpUploadNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return sftp_upload(ctx)


@builtin_node_type(
    type_id="ssh_sftp.download",
    display_name="SFTP Download",
    category_path=SSH_SFTP_CATEGORY,
    description="Download files or directories from a remote machine via SFTP.",
    keywords=("Linux", "Unix", "SSH", "FTP", "SCP", "Get", "HPC", "Transfer"),
    ports=(
        PortSpec(
            "target_host",
            "in",
            "data",
            'SSH_SFTP_Connector.Nodes.Control.SSH_SFTP.SshSftpHostData',
            label="Target Host",
            required=True,
            description="Target SSH/SFTP Host to download from.",
        ),
        PortSpec(
            "sources",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Sources",
            required=True,
            data_access="list",
            description="Source files or directories to download.",
        ),
        PortSpec(
            "destination",
            "in",
            "data",
            'COREX.DataTypes.String',
            label="Destination",
            required=True,
            description=(
                "Destination file or directory to download to. You can use . as the "
                "destination to download to the current working directory."
            ),
        ),
        PortSpec(
            "overwrite",
            "in",
            "data",
            'COREX.DataTypes.Bool',
            label="Overwrite existing files",
            required=False,
            uses_property_default=True,
            description="Allow overwriting if the source already exists in the destination.",
        ),
        PortSpec(
            "successful",
            "out",
            "data",
            'COREX.DataTypes.Bool',
            label="Successful",
            description="'True' if the download was successful.",
        ),
        PortSpec(
            "downloaded_bytes",
            "out",
            "data",
            'COREX.DataTypes.Int',
            label="Downloaded bytes",
            description="Amount of bytes Downloaded.",
        ),
        PortSpec(
            "downloaded_files",
            "out",
            "data",
            'COREX.DataTypes.Int',
            label="Downloaded files",
            description="Amount of files Downloaded.",
        ),
    ),
    properties=(PropertySpec("overwrite", "bool", False, "Overwrite existing files"),),
)
class SftpDownloadNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return sftp_download(ctx)


SSH_SFTP_NODE_DESCRIPTORS = (
    plugin_descriptor(SecretNodePlugin),
    plugin_descriptor(SshSftpHostNodePlugin),
    plugin_descriptor(RunSshCommandNodePlugin),
    plugin_descriptor(RunSshScriptNodePlugin),
    plugin_descriptor(SftpUploadNodePlugin),
    plugin_descriptor(SftpDownloadNodePlugin),
)


__all__ = [
    "SSH_SFTP_DATA_TYPE_FAMILIES",
    "SSH_SFTP_DATA_TYPE_OWNER_ID",
    "SSH_SFTP_DATA_TYPES",
    "SSH_SFTP_HOST_DATA_TYPE_ID",
    "SSH_SFTP_NODE_DESCRIPTORS",
    "SSH_SFTP_SECRET_DATA_TYPE_ID",
]

from __future__ import annotations

from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type_spec
import smtplib
from email.message import EmailMessage

from ea_node_editor.nodes.decorators import plugin_descriptor
from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
    PropertyConditionSpec,
    ReadinessRequirementSpec,
)
from ea_node_editor.runtime_contracts.data_tree import resolve_single_run_inputs


def split_recipients(value: str) -> list[str]:
    normalized = value.replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


class EmailSendNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="io.email_send",
            display_name="Email Send",
            category_path=("Input / Output",),
            description="Sends a plaintext email through a configured SMTP server.",
            keywords=("email", "smtp", "notification"),
            ports=(
                PortSpec(
                    "subject",
                    "in",
                    "data",
                    'COREX.DataTypes.String',
                    required=False,
                    uses_property_default=True,
                    data_access="tree",
                    description="Email subject; overrides the configured Subject property when connected.",
                ),
                PortSpec(
                    "body",
                    "in",
                    "data",
                    'COREX.DataTypes.String',
                    required=False,
                    uses_property_default=True,
                    data_access="tree",
                    description="Plaintext email body; overrides the configured Body property when connected.",
                ),
                PortSpec(
                    "sent",
                    "out",
                    "data",
                    'COREX.DataTypes.Bool',
                    exposed=True,
                    description="True after the SMTP server accepts the message.",
                ),
            ),
            properties=(
                PropertySpec("smtp_host", "str", "localhost", "SMTP Host"),
                PropertySpec("smtp_port", "int", 25, "SMTP Port"),
                PropertySpec("username", "str", "", "Username"),
                PropertySpec("password", "str", "", "Password"),
                PropertySpec("sender", "str", "", "Sender"),
                PropertySpec("to", "str", "", "To"),
                PropertySpec("subject", "str", "COREX Node Editor Notification", "Subject"),
                PropertySpec("body", "str", "Workflow run completed.", "Body"),
                PropertySpec("use_tls", "bool", False, "Use TLS"),
            ),
            readiness_requirements=(
                ReadinessRequirementSpec(any_of_properties=("smtp_host",)),
                ReadinessRequirementSpec(any_of_properties=("sender",)),
                ReadinessRequirementSpec(any_of_properties=("to",)),
                ReadinessRequirementSpec(
                    any_of_properties=("password",),
                    when_properties=(PropertyConditionSpec("username"),),
                ),
            ),
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        inputs = resolve_single_run_inputs(ctx.inputs, node_name="Email Send")
        smtp_host = str(ctx.properties.get("smtp_host", "localhost")).strip()
        smtp_port = int(ctx.properties.get("smtp_port", 25))
        username = str(ctx.properties.get("username", ""))
        password = str(ctx.properties.get("password", ""))
        sender = str(ctx.properties.get("sender", "")).strip()
        recipient = str(ctx.properties.get("to", ""))
        subject = str(inputs.get("subject", ctx.properties.get("subject", "")))
        body = str(inputs.get("body", ctx.properties.get("body", "")))
        recipients = split_recipients(recipient)
        if smtp_port <= 0:
            raise ValueError(f"Email Send SMTP port must be a positive integer. Received: {smtp_port}")

        message = EmailMessage()
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=10) as smtp:
                if bool(ctx.properties.get("use_tls", False)):
                    smtp.starttls()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
        except smtplib.SMTPException as exc:
            raise RuntimeError(f"Email Send SMTP error ({smtp_host}:{smtp_port}): {exc}") from exc
        except OSError as exc:
            raise RuntimeError(
                f"Email Send could not connect to SMTP server {smtp_host}:{smtp_port}: {exc}"
            ) from exc
        return NodeResult(outputs={"sent": True})


EMAIL_NODE_DESCRIPTORS = (plugin_descriptor(EmailSendNodePlugin),)

from __future__ import annotations

import smtplib
from email.message import EmailMessage

from ea_node_editor.nodes.execution_context import NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec


def split_recipients(value: str) -> list[str]:
    normalized = value.replace(";", ",")
    return [item.strip() for item in normalized.split(",") if item.strip()]


class EmailSendNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="io.email_send",
            display_name="Email Send",
    category_path=("Input / Output",),
            icon="mail",
            description="Sends a plaintext email using SMTP.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=False),
                PortSpec("subject", "in", "data", "str", required=False),
                PortSpec("body", "in", "data", "str", required=False),
                PortSpec("sent", "out", "data", "bool", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
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
        )

    def execute(self, ctx) -> NodeResult:  # noqa: ANN001
        smtp_host = str(ctx.properties.get("smtp_host", "localhost")).strip()
        smtp_port = int(ctx.properties.get("smtp_port", 25))
        username = str(ctx.properties.get("username", ""))
        password = str(ctx.properties.get("password", ""))
        sender = str(ctx.properties.get("sender", "")).strip()
        recipient = str(ctx.properties.get("to", ""))
        subject = str(ctx.inputs.get("subject", ctx.properties.get("subject", "")))
        body = str(ctx.inputs.get("body", ctx.properties.get("body", "")))
        recipients = split_recipients(recipient)
        if not smtp_host:
            raise ValueError("Email Send requires SMTP host.")
        if smtp_port <= 0:
            raise ValueError(f"Email Send SMTP port must be a positive integer. Received: {smtp_port}")
        if not sender:
            raise ValueError("Email Send requires sender email address.")
        if not recipients:
            raise ValueError("Email Send requires at least one recipient in 'to'.")
        if username and not password:
            raise ValueError("Email Send requires password when username is provided.")

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
        return NodeResult(outputs={"sent": True, "exec_out": True})

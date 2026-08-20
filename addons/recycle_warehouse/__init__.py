import base64
import logging
import os

from . import models
from . import controllers

_logger = logging.getLogger(__name__)


def _set_company_logo(env):
    """Stamp the Dawrha logo as the COMPANY logo, so `web.external_layout` prints
    it at the top of every report instead of Odoo's grey "Your Logo" placeholder.

    Setting it here — once, from the addon's own asset — is why the shipment /
    order PDFs carry the brand without anyone uploading an image in Settings, and
    why the header shows OUR logo rather than the empty placeholder. Best-effort:
    a missing file must never block installation."""
    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'src', 'img', 'Logo.png')
    try:
        with open(logo_path, 'rb') as fh:
            encoded = base64.b64encode(fh.read())
        # Every company (there is normally one) gets the brand.
        env['res.company'].sudo().search([]).write({'logo': encoded})
        _logger.info('Company logo set to the Dawrha brand for report headers.')
    except Exception as exc:  # noqa: BLE001 - reported, never fatal
        _logger.warning('Could not set the company logo: %s', exc)


def _configure_backend_sync(env):
    """Wire the backend integration FROM THE ENVIRONMENT — dynamic, per-deploy.

    The two-way sync depends on three system parameters: where the NestJS
    backend lives and the shared secret that signs the outbound pings. They used
    to be typed by hand into Technical → System Parameters, so a fresh
    environment synced NOTHING and gave no hint why (a truck/warehouse created
    here never reached the backend).

    Here they are seeded from environment variables on install/upgrade, so the
    same image runs in dev, staging and production and each just declares its own
    values — no code change, no manual DB edit. The ENVIRONMENT wins: a value
    present in the env overwrites whatever was there, so deployment config is the
    single source of truth. An empty/absent env var is left untouched, so a value
    set by hand is not wiped by a redeploy that simply did not pass it.

    Recognised variables:
      RECYCLE_BACKEND_BASE_URL       e.g. https://api.dawrha.com
                                     (or http://host.docker.internal:3000 in dev)
      RECYCLE_BACKEND_WEBHOOK_SECRET must match the backend ODOO_WEBHOOK_SECRET
      RECYCLE_BACKEND_API_KEY        optional extra header for the outbound calls
    """
    icp = env['ir.config_parameter'].sudo()
    mapping = {
        'RECYCLE_BACKEND_BASE_URL': 'recycle.backend_base_url',
        'RECYCLE_BACKEND_WEBHOOK_SECRET': 'recycle.backend_webhook_secret',
        'RECYCLE_BACKEND_API_KEY': 'recycle.backend_api_key',
    }
    for env_key, param_key in mapping.items():
        value = (os.environ.get(env_key) or '').strip()
        if value:
            icp.set_param(param_key, value)
            shown = value if 'SECRET' not in env_key and 'KEY' not in env_key else '***'
            _logger.info('Backend sync configured from env: %s = %s', param_key, shown)


def post_init_hook(env):
    """Enable free signup, seed the Set Password email template, wire the backend
    sync from the environment, and brand the report header with the app logo."""
    _configure_backend_sync(env)
    _set_company_logo(env)

    # Enable free signup on the website
    env['ir.config_parameter'].sudo().set_param(
        'auth_signup.invitation_scope', 'b2c')
    Website = env['website'].sudo()
    if 'auth_signup_uninvited' in Website._fields:
        Website.search([]).write({'auth_signup_uninvited': 'b2c'})

    # Create / update "Set Password" email template
    Template = env['mail.template'].sudo()
    existing = Template.search([
        ('model_id.model', '=', 'res.users'),
        ('name', '=', 'Recycle: Set Password'),
    ], limit=1)

    body_html = '''
    <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:auto;
                background:#ffffff;border-radius:16px;overflow:hidden;
                border:1px solid #e2e8f0;">
        <div style="background:linear-gradient(135deg,#047857,#10b981);
                    padding:24px 28px;color:#fff;">
            <div style="font-size:24px;font-weight:900;">Dawrha</div>
            <div style="opacity:.9;font-size:14px;margin-top:2px;">Set Up Your Password</div>
        </div>
        <div style="padding:28px;">
            <p style="font-size:16px;color:#0f172a;margin:0 0 14px;">
                Dear {{ object.name or '' }},
            </p>
            <p style="font-size:15px;color:#334155;line-height:1.6;margin:0 0 20px;">
                Your account has been created on the Dawrha platform. To start using the system,
                please set your personal password by clicking the button below.
            </p>
            <div style="text-align:center;margin:28px 0;">
                <a href="{{ object._get_reset_password_url() }}"
                   style="display:inline-block;background:linear-gradient(135deg,#047857,#10b981);
                          color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;
                          padding:14px 36px;border-radius:10px;letter-spacing:0.3px;">
                    Set Password
                </a>
            </div>
            <div style="background:#f8fafc;border-radius:10px;padding:16px 20px;margin:20px 0;
                        border:1px solid #e2e8f0;">
                <p style="font-size:13px;color:#64748b;margin:0 0 6px;font-weight:600;">
                    Your login credentials:</p>
                <p style="font-size:14px;color:#0f172a;margin:0;">
                    Login: <strong>{{ object.login or '' }}</strong>
                </p>
            </div>
            <p style="font-size:13px;color:#94a3b8;line-height:1.6;margin-top:20px;">
                This link will expire in 24 hours. If you did not expect this email,
                please contact your warehouse manager.
            </p>
            <p style="font-size:13px;color:#94a3b8;margin-top:18px;">— The Dawrha Team</p>
        </div>
    </div>
    '''

    vals = {
        'name': 'Recycle: Set Password',
        'model_id': env.ref('base.model_res_users').id,
        'subject': 'Dawrha — Set Up Your Account Password',
        'email_from': "{{ (object.company_id.email or 'noreply@dawrha.com') }}",
        'email_to': '{{ object.email }}',
        'body_html': body_html,
        'lang': '{{ object.lang }}',
        'auto_delete': True,
    }

    if existing:
        existing.write(vals)
    else:
        Template.create(vals)

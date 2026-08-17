from . import models
from . import controllers


def post_init_hook(env):
    """Enable free signup and create Set Password email template."""
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

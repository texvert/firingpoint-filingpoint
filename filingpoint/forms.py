from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, ValidationError

from .passwords import password_problem


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])


class LogoutForm(FlaskForm):
    pass


class NewPasswordForm(FlaskForm):
    new_password = PasswordField("New password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Repeat new password",
        validators=[DataRequired(), EqualTo("new_password", message="The new passwords don't match.")],
    )

    def validate_new_password(self, field):
        problem = password_problem(field.data)
        if problem is not None:
            raise ValidationError(problem)


class ChangePasswordForm(NewPasswordForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])

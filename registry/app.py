"""The app module, containing the app factory function."""
import logging
import sys

from flask import Flask, flash, redirect, url_for

from registry import batch, commands, donor, public, user
from registry.extensions import (
    bcrypt,
    csrf_protect,
    db,
    debug_toolbar,
    login_manager,
    migrate,
)
from registry.utils import template_globals


def create_app(config_object="registry.settings"):
    """Create application factory, as explained here:
    http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)
    app.context_processor(template_globals)
    register_extensions(app)
    register_blueprints(app)
    register_commands(app)
    configure_logger(app)

    @app.errorhandler(404)
    def page_not_found(e):
        flash("404 - Stránka, kterou hledáte, neexistuje.", "danger")
        return redirect(url_for("public.home", status_code=404))

    @app.errorhandler(401)
    def unauthorized(e):
        flash("401 - Nejste přihlášeni. Pro pokračování se prosím přihlaste.", "danger")
        return redirect(url_for("public.home", status_code=401))

    @app.template_filter("format_time")
    def format_time(date, format="%d.%m.%Y %H:%M:%S"):
        return date.strftime(format)

    @app.template_filter("translate")
    def translate(input, rodne_cislo):
        word_map = {
            "pracovník": "pracovnice",
            "p.": "pí",
            "ocenit jeho hluboce": "ocenit její hluboce",
            "využijete jeho příkladu": "využijete jejího příkladu",
        }
        if rodne_cislo[2] in ("5", "6", "7", "8"):
            return word_map[input]
        else:
            return input

    return app


def register_extensions(app):
    """Register Flask extensions."""
    bcrypt.init_app(app)
    db.init_app(app)
    csrf_protect.init_app(app)
    login_manager.init_app(app)
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(public.views.blueprint)
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(donor.views.blueprint)
    app.register_blueprint(batch.views.blueprint)
    return None


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.create_user)
    app.cli.add_command(commands.install_test_data)
    app.cli.add_command(commands.refresh_overview)


def configure_logger(app):
    """Configure loggers."""
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)

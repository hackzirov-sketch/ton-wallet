from flask import Blueprint, render_template, redirect, url_for, flash, request
from app.models import AppSetting
from app.services.ton_utils import validate_ton_address, normalize_address
from app.services.wallet_sync import sync_wallet
from app.extensions import db
from flask import current_app

wallet_bp = Blueprint("wallet", __name__)


@wallet_bp.route("/setup", methods=["GET", "POST"])
def setup():
    setting = AppSetting.get_active_wallet()
    if setting and setting.last_sync_at:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        address = request.form.get("wallet_address", "").strip()
        if not validate_ton_address(address):
            flash("Invalid TON wallet address. Please enter a valid address starting with EQ or UQ.", "error")
            return render_template("wallet_setup.html")

        address = normalize_address(address)
        AppSetting.set_wallet(address)

        try:
            sync_wallet(address, current_app.config)
            flash("Wallet connected and synced successfully!", "success")
        except Exception as e:
            flash(f"Wallet saved but sync failed: {str(e)}. You can retry from the dashboard.", "warning")

        return redirect(url_for("dashboard.index"))

    return render_template("wallet_setup.html")


@wallet_bp.route("/change-wallet", methods=["GET", "POST"])
def change_wallet():
    setting = AppSetting.get_active_wallet()

    if request.method == "POST":
        address = request.form.get("wallet_address", "").strip()
        confirm = request.form.get("confirm", "")

        if confirm != "yes":
            flash("Please confirm the wallet change.", "error")
            return render_template("change_wallet.html", current_wallet=setting.wallet_address if setting else None)

        if not validate_ton_address(address):
            flash("Invalid TON wallet address.", "error")
            return render_template("change_wallet.html", current_wallet=setting.wallet_address if setting else None)

        address = normalize_address(address)

        from app.models import Transaction, SyncLog
        if setting:
            Transaction.query.filter_by(wallet_address=setting.wallet_address).delete()
            SyncLog.query.filter_by(wallet_address=setting.wallet_address).delete()
            db.session.commit()

        AppSetting.set_wallet(address)

        try:
            sync_wallet(address, current_app.config)
            flash("Wallet changed and synced successfully!", "success")
        except Exception as e:
            flash(f"New wallet saved but sync failed: {str(e)}. You can retry from the dashboard.", "warning")

        return redirect(url_for("dashboard.index"))

    return render_template("change_wallet.html", current_wallet=setting.wallet_address if setting else None)

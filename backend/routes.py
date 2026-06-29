from flask import jsonify
from backend.adapter import get_dashboard,get_analysis,get_history,get_settings
from backend.status import get_status


def register_routes(app):

    @app.route("/")
    def home():
        return jsonify({
            "backend": "Flask",
            "project": "BTC SMC ICT Engine",
            "status": "running",
            "version": "0.2"
        })


    @app.route("/health")
    def health():
        return jsonify({
            "status": "ok"
        })


    @app.route("/api/dashboard")
    def dashboard():
        try:
            return jsonify(get_dashboard())
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500


    @app.route("/api/analysis")
    def analysis():

        try:

            return jsonify(get_analysis())

        except Exception as e:

            return jsonify({

                "status":"error",

                "message":str(e)

            }),500



    @app.route("/api/history")

    def history():

        try:

            return jsonify(get_history())

        except Exception as e:

            return jsonify({

                "status":"error",

                "message":str(e)

            }),500



    @app.route("/api/status")
    def api_status():
        return jsonify(get_status())


    @app.route("/api/settings")
    def settings_api():
        return jsonify(get_settings())

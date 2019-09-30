from flask_restplus import Resource, Namespace, fields
from models.models import GameState, CellState, Game as GameDb, Cell
from flask import request
from common.app import db

ns = Namespace("Game", description="Games related operations")
_new_game = ns.model("New game", {
    "rows": fields.Integer(required=True, description="Number of rows"),
    "columns": fields.Integer(required=True, description="Number of columns"),
    "mines": fields.Integer(required=True, description="Number of mines"),
})

_action = ns.model("Action", {
    "x": fields.Integer(required=True, description="Cell row"),
    "y": fields.Integer(required=True, description="Cell column"),
    "action": fields.String(required=True, description="Cell action", enum=["Flag", "Question", "Press"]),
})


_game_status = ns.model("Games status", {
    "id": fields.Integer(required=True, description="Game identifier"),
    "state": fields.String(required=True, description="Game status", enum=list(GameState.__members__.keys())),
})


_cell = ns.model("Cell", {
    "x": fields.Integer(required=True, description="Grid row"),
    "y": fields.Integer(required=True, description="Grid column"),
    "state": fields.String(required=True, description="Game status", enum=list(CellState.__members__.keys())),
    "bombs_around": fields.Integer(description="Number of bombs around a pressed cell")
})

_game = ns.inherit("Game", _game_status, {
    "rows": fields.Integer(required=True, description="Number of rows"),
    "columns": fields.Integer(required=True, description="Number of columns"),
    "mines": fields.Integer(required=True, description="Number of bombs"),
    "started_at": fields.DateTime(required=True, description="When the game started"),
    "finished_at": fields.DateTime(required=False, description="When the game finished"),
    "grid": fields.List(fields.Nested(_cell))
})


@ns.route("/")
class GameList(Resource):
    @ns.doc("List of games with its current status")
    @ns.marshal_list_with(_game_status, envelope="data")
    def get(self):
        return GameDb.list_all()

    @ns.doc("Create a new game")
    @ns.expect(_new_game, validate=True)
    @ns.marshal_with(_game, envelope="data", code=201)
    def post(self):
        data = request.json
        game = GameDb(**data)
        db.session.add(game)
        db.session.flush()
        Cell.generate_grid(game)
        db.session.commit()

        return game


@ns.route("/<game_id>")
@ns.param("game_id", "The game identifier")
@ns.response(404, "Game not found.")
class Game(Resource):
    @ns.doc("Get full data of a game")
    @ns.marshal_with(_game, envelope="data")
    def get(self, game_id):
        return GameDb.query.get(game_id)

    @ns.doc("Apply and action on a cell")
    @ns.marshal_with(_game, envelope="data")
    @ns.expect(_action, validate=True)
    def put(self, game_id):
        data = request.json
        cell = Cell.query.filter_by(game_id=game_id, x=data["x"], y=data["y"]).one()

        if not cell.state == CellState.CLEARED:
            if data["action"] == "Flag":
                cell.state = CellState.RED_FLAGGED
            if data["action"] == "Question":
                cell.state = CellState.QUESTIONED
            if data["action"] == "Press":
                if cell.has_bomb:
                    cell.state = CellState.BOMBED
                else:
                    cell.state = CellState.CLEARED

            db.session.add(cell)
            db.session.commit()

        return GameDb.query.get(game_id)

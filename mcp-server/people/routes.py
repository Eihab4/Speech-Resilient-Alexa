import logging
from http import HTTPStatus

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from memory import Helper, MemoryStore, Profile
from messages import TELEGRAM_LINK, ErrorMessage
from notify import TelegramBot, TelegramError

logger = logging.getLogger(__name__)


class ProfileRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    home_address: str | None = None


class HelperRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(min_length=1)
    name: str = Field(min_length=1)


def _error(message: ErrorMessage, status: HTTPStatus) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _invalid(error: ValidationError) -> JSONResponse:
    fields = {location for problem in error.errors() for location in problem["loc"]}
    message = ErrorMessage.USER_ID_MISSING if "user_id" in fields else ErrorMessage.NAME_MISSING
    return _error(message, HTTPStatus.BAD_REQUEST)


def create_people_routes(store: MemoryStore, bot: TelegramBot | None, company_id: str) -> list[Route]:
    """Setup done once by the family on the page: who the person is, and who gets their emergency alerts.
    Plain routes, not MCP tools, so they stay out of the tools an AI host chooses from."""

    async def bot_name() -> str | None:
        if bot is None:
            return None
        try:
            return await run_in_threadpool(bot.username)
        except TelegramError:
            logger.exception(ErrorMessage.TELEGRAM_UNREACHABLE.format(method="getMe"))
            return None

    def helper_json(helper: Helper, username: str | None) -> dict:
        # The link is only shown until the helper opens it.
        link = None if helper.linked or not username else TELEGRAM_LINK.format(username=username, code=helper.link_code)
        return {"id": helper.id, "name": helper.name, "linked": helper.linked, "link": link}

    def user_id_of(request: Request) -> str:
        return request.query_params.get("user_id", "").strip()

    async def get_profile(request: Request) -> Response:
        if not (user_id := user_id_of(request)):
            return _error(ErrorMessage.USER_ID_MISSING, HTTPStatus.BAD_REQUEST)
        profile = store.profile(company_id, user_id) or Profile(name="")
        return JSONResponse(profile.model_dump())

    async def save_profile(request: Request) -> Response:
        try:
            body = ProfileRequest.model_validate_json(await request.body())
        except ValidationError as error:
            return _invalid(error)
        profile = Profile(name=body.name, home_address=body.home_address or None)
        store.save_profile(company_id, body.user_id, profile)
        return JSONResponse(profile.model_dump())

    async def list_helpers(request: Request) -> Response:
        if not (user_id := user_id_of(request)):
            return _error(ErrorMessage.USER_ID_MISSING, HTTPStatus.BAD_REQUEST)
        username = await bot_name()
        helpers = [helper_json(helper, username) for helper in store.helpers(company_id, user_id)]
        return JSONResponse({"telegram": username is not None, "helpers": helpers})

    async def add_helper(request: Request) -> Response:
        try:
            body = HelperRequest.model_validate_json(await request.body())
        except ValidationError as error:
            return _invalid(error)
        helper = store.add_helper(company_id, body.user_id, Helper(name=body.name))
        return JSONResponse(helper_json(helper, await bot_name()), status_code=HTTPStatus.CREATED)

    async def remove_helper(request: Request) -> Response:
        if not store.remove_helper(company_id, user_id_of(request), request.path_params["helper_id"]):
            return _error(ErrorMessage.HELPER_NOT_FOUND, HTTPStatus.NOT_FOUND)
        return Response(status_code=HTTPStatus.NO_CONTENT)

    return [
        Route("/profile", get_profile, methods=["GET"]),
        Route("/profile", save_profile, methods=["PUT"]),
        Route("/helpers", list_helpers, methods=["GET"]),
        Route("/helpers", add_helper, methods=["POST"]),
        Route("/helpers/{helper_id}", remove_helper, methods=["DELETE"]),
    ]

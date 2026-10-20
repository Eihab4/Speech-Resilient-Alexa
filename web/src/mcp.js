import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";

import { CLIENT_INFO, MCP_URL } from "./config.js";
import { NextMove, Tool } from "./enums.js";
import { signedIn } from "./http.js";
import { ErrorMessage } from "./messages.js";

let connection;
let connectedAs;

function connect(token) {
  if (connectedAs !== token) connection = undefined;
  connectedAs = token;
  connection ??= (async () => {
    const client = new Client(CLIENT_INFO);
    await client.connect(new StreamableHTTPClientTransport(new URL(MCP_URL), { requestInit: signedIn(token) }));
    return client;
  })();
  return connection;
}

async function send(name, args, token) {
  const client = await connect(token);
  return client.callTool({ name, arguments: args });
}

async function callTool(name, args, token) {
  let result;
  try {
    result = await send(name, args, token);
  } catch {
    // The connection broke (e.g. the server restarted and forgot our session). Reconnect once.
    connection = undefined;
    result = await send(name, args, token).catch((error) => {
      connection = undefined;
      throw new Error(ErrorMessage.unreachable(MCP_URL), { cause: error });
    });
  }

  if (result.isError) {
    throw new Error(result.content?.[0]?.text ?? ErrorMessage.toolFailed(name));
  }
  return result.structuredContent ?? JSON.parse(result.content?.[0]?.text ?? "{}");
}

// With no AI host in the page, this plays Alexa's part: it makes the follow-up call
// that understand_speech asks for.
export async function takeTurn(token, heard, pausesMs = []) {
  const args = { heard, ...(pausesMs.length ? { pauses_ms: pausesMs } : {}) };
  const decision = await callTool(Tool.UNDERSTAND_SPEECH, args, token);

  if (decision.next_move === NextMove.CANCEL) {
    return { ...decision, ...(await callTool(Tool.CANCEL_REQUEST, {}, token)) };
  }

  if (decision.next_move === NextMove.DONE) {
    return { ...decision, ...(await callTool(Tool.DO_CONFIRMED_REQUEST, { pending_id: decision.pending_id }, token)) };
  }

  if (decision.next_move === NextMove.HELP) {
    const help = await callTool(Tool.ASK_FOR_HELP, {}, token);
    return { ...decision, ...help, say: `${decision.say} ${help.say}` };
  }

  return decision;
}

export function sendSos(token, position) {
  return callTool(Tool.EMERGENCY_SOS, position, token);
}

export function speechTrend(token) {
  return callTool(Tool.SPEECH_TREND, {}, token);
}

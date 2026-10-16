import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";

import { CLIENT_INFO, MCP_URL } from "./config.js";
import { NextMove, Tool } from "./enums.js";
import { ErrorMessage } from "./messages.js";

let connection;

function connect() {
  connection ??= (async () => {
    const client = new Client(CLIENT_INFO);
    await client.connect(new StreamableHTTPClientTransport(new URL(MCP_URL)));
    return client;
  })();
  return connection;
}

async function send(name, args) {
  const client = await connect();
  return client.callTool({ name, arguments: args });
}

async function callTool(name, args) {
  let result;
  try {
    result = await send(name, args);
  } catch {
    // The connection broke (e.g. the server restarted and forgot our session). Reconnect once.
    connection = undefined;
    result = await send(name, args).catch((error) => {
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
export async function takeTurn(userId, heard) {
  const decision = await callTool(Tool.UNDERSTAND_SPEECH, { user_id: userId, heard });

  if (decision.next_move === NextMove.CANCEL) {
    return { ...decision, ...(await callTool(Tool.CANCEL_REQUEST, { user_id: userId })) };
  }

  if (decision.next_move === NextMove.DONE) {
    const pendingId = decision.pending_id;
    return { ...decision, ...(await callTool(Tool.DO_CONFIRMED_REQUEST, { user_id: userId, pending_id: pendingId })) };
  }

  return decision;
}

export function sendSos(userId, position) {
  return callTool(Tool.EMERGENCY_SOS, { user_id: userId, ...position });
}

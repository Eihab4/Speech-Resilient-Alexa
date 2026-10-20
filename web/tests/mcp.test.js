import { beforeEach, expect, test, vi } from "vitest";

import { NextMove, Tool } from "../src/enums.js";

const calls = [];
let answers = {};

vi.mock("@modelcontextprotocol/client", () => ({
  Client: class {
    async connect() {}
    async callTool({ name, arguments: args }) {
      calls.push([name, args]);
      return { structuredContent: answers[name] };
    }
  },
  StreamableHTTPClientTransport: class {},
}));

const { speechTrend, takeTurn } = await import("../src/mcp.js");

beforeEach(() => {
  calls.length = 0;
  answers = {};
});

test("a done move carries the request out with its pending id", async () => {
  answers = {
    [Tool.UNDERSTAND_SPEECH]: { next_move: NextMove.DONE, pending_id: "p_1", say: "Okay." },
    [Tool.DO_CONFIRMED_REQUEST]: { say: "Done. Calling Mom." },
  };

  const result = await takeTurn("t1", "yes");

  expect(calls).toEqual([
    [Tool.UNDERSTAND_SPEECH, { heard: "yes" }],
    [Tool.DO_CONFIRMED_REQUEST, { pending_id: "p_1" }],
  ]);
  expect(result.say).toBe("Done. Calling Mom.");
});

test("a help move tells the helper at once and says both sentences", async () => {
  answers = {
    [Tool.UNDERSTAND_SPEECH]: { next_move: NextMove.HELP, pending_id: "p_1", say: "Okay, I'll ask your helper." },
    [Tool.ASK_FOR_HELP]: { sent: true, sent_to: ["Sara"], say: "I sent Sara what I understood so far. Go on." },
  };

  const result = await takeTurn("t1", "help", [1200]);

  expect(calls).toEqual([
    [Tool.UNDERSTAND_SPEECH, { heard: "help", pauses_ms: [1200] }],
    [Tool.ASK_FOR_HELP, {}],
  ]);
  expect(result.next_move).toBe(NextMove.HELP);
  expect(result.sent_to).toEqual(["Sara"]);
  expect(result.say).toBe("Okay, I'll ask your helper. I sent Sara what I understood so far. Go on.");
});

test("the trend is asked for the signed-in person", async () => {
  answers = { [Tool.SPEECH_TREND]: { days: [], say: "We haven't finished a request together yet." } };

  const result = await speechTrend("t1");

  expect(calls).toEqual([[Tool.SPEECH_TREND, {}]]);
  expect(result.say).toBe("We haven't finished a request together yet.");
});

import { NextMove } from "./enums.js";

const State = Object.freeze({
  IDLE: "idle",
  ARMED: "armed", // the server said sos; waiting for Alexa to finish saying so
  COUNTING: "counting",
  DUE: "due", // the countdown ended; the alert goes out once the turns already sent are answered
});

// The countdown before an emergency alert. Silence sends it. Any reply other than sos clears it,
// because the server answers "stop" with a normal move.
export function createSos({ readPosition, onTick, onDue }) {
  let state = State.IDLE;
  let timer = null;
  let left = 0;
  let position = null;

  function clear() {
    clearInterval(timer);
    timer = null;
  }

  function tick() {
    left -= 1;
    if (left > 0) return onTick(left);
    clear();
    state = State.DUE;
    onTick(0);
    onDue();
  }

  return {
    get state() {
      return state;
    },
    // Called with every reply to a turn.
    follow(result) {
      if (result.next_move !== NextMove.SOS) {
        if (state === State.COUNTING) onTick(0);
        clear();
        state = State.IDLE;
        return;
      }
      if (state !== State.IDLE) return;
      state = State.ARMED;
      left = result.countdown_seconds;
      position = readPosition();
    },
    // Called when Alexa stops talking: the person can only say stop once the mic is back.
    begin() {
      if (state !== State.ARMED) return;
      state = State.COUNTING;
      onTick(left);
      timer = setInterval(tick, 1000);
    },
    // The position to send with the alert, or null when nothing is due (the person said stop in time).
    take() {
      if (state !== State.DUE) return null;
      state = State.IDLE;
      return position;
    },
  };
}

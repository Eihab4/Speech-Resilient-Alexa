export const SOS_PHRASES = Object.freeze(["i fell", "i fall", "fell down", "emergency", "sos", "ambulance"]);

const SOS_PATTERN = new RegExp(`\\b(${SOS_PHRASES.join("|")})\\b`);

export function plainWords(heard) {
  return (heard.toLowerCase().replaceAll("’", "'").match(/[a-z']+/g) ?? []).join(" ");
}

export function asksForSos(heard) {
  const words = plainWords(heard);
  return SOS_PATTERN.test(words) || words.split(" ").filter((word) => word === "help").length >= 2;
}

import { construirCallback, parsearCallback } from "./telegram.ts";

function assert(cond: unknown, msg = "Falló la comprobación") {
  if (!cond) throw new Error(msg);
}

Deno.test("construirCallback arma datos cortos", () => {
  assert(construirCallback("confirmar", 42) === "confirmar:42");
  assert(construirCallback("enviar", 1, 25) === "enviar:1:25");
});

Deno.test("construirCallback rechaza más de 64 bytes", () => {
  let fallo = false;
  try {
    construirCallback("x".repeat(64), 1);
  } catch {
    fallo = true;
  }
  assert(fallo, "Debía lanzar por longitud");
});

Deno.test("parsearCallback válido de dos y tres partes", () => {
  const a = parsearCallback("confirmar:42");
  assert(a && a.tipo === "confirmar" && a.args[0] === "42");
  const b = parsearCallback("enviar:1:25");
  assert(b && b.tipo === "enviar" && b.args.join(",") === "1,25");
});

Deno.test("parsearCallback rechaza vacío y caracteres inválidos", () => {
  assert(parsearCallback("") === null);
  assert(parsearCallback("tipo:###") === null);
  assert(parsearCallback("tipo:" + "a".repeat(24)) === null);
});

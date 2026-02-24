import { composeEnv } from "./setup";

export default async function teardown() {
  if (composeEnv) {
    await composeEnv.down();
  }
}

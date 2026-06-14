export const PonytailPlugin = async ({ project, client, $, directory, worktree }) => {

  return {

    // Ensure generated Python files have proper structure
    "tool.execute.before": async (input, output) => {

      // For edit/write operations, validate Python files
      if (input.tool === "write" || input.tool === "edit") {
        const filePath = output.args?.filePath || "";
        if (filePath.endsWith(".py") && output.args?.content) {
          const content = output.args.content;
          const lines = content.split("\n");

          // Auto-add newline at EOF if missing
          if (lines.length > 0 && lines[lines.length - 1] !== "") {
            output.args.content = content + "\n";
          }

          // Flag missing docstrings on public functions
          const funcPattern = /^async\s+def\s+|^def\s+/;
          for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (
              funcPattern.test(line) &&
              !line.startsWith("def _") &&
              !line.startsWith("async def _")
            ) {
              // Check next non-empty, non-decorator line isn't a docstring
              let j = i + 1;
              while (j < lines.length && (lines[j].trim() === "" || lines[j].trim().startsWith("@"))) {
                j++;
              }
              if (j < lines.length && !lines[j].trim().startsWith('"') && !lines[j].trim().startsWith("'")) {
                await client.app.log({
                  body: {
                    service: "ponytail",
                    level: "warn",
                    message: `Missing docstring: ${line.replace(/^(async\s+)?def\s+/, "")} at line ${i + 1} in ${filePath}`,
                  },
                });
              }
            }
          }
        }
      }
    },

    // Log session events for debugging
    event: async ({ event }) => {
      if (event.type === "session.error") {
        await client.app.log({
          body: {
            service: "ponytail",
            level: "error",
            message: `Session error: ${event.error?.message || "unknown"}`,
          },
        });
      }
    },
  };
};

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY toolbox /usr/local/bin/toolbox
RUN chmod +x /usr/local/bin/toolbox

ENV PORT=8080

ENTRYPOINT ["toolbox", "serve", "--prebuilt", "dataplex", "--address", "0.0.0.0", "--port", "8080"]

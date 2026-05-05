YAML  := tanzpalast.yaml
JSON  := data/tanzpalast-data.json
INDEX := data/drive-index.json

.PHONY: all scan stubs build thumbnails publish preview clean help

all: thumbnails build

# --- Drive ---

scan:
	uv run python src/list_drive.py

stubs:
	@test -f $(INDEX) || { echo "ERROR: $(INDEX) not found — run 'make scan' first"; exit 1; }
	@uv run python src/new_filenames.py | while IFS= read -r fn; do \
	  echo ">> inferring placement for $$fn"; \
	  uv run python src/stub_input.py "$$fn" \
	  | claude -p "$$(cat prompts/insert_video.md)" \
	  | tee /tmp/claude_last.json \
	  | uv run python src/apply_insert.py \
	  || { echo "  !! $$fn failed — Claude output in /tmp/claude_last.json"; }; \
	done

# --- Build ---

build: $(JSON)

$(JSON): $(YAML)
	uv run python src/build.py

# --- Thumbnails ---

thumbnails:
	uv run python src/make_thumbnails.py

# --- Publish ---

publish: all
	git add $(YAML) $(JSON) $(INDEX) thumbnails/
	git diff --cached --quiet || git commit -m "update catalog"
	git push

# --- Misc ---

preview:
	@python3 -m http.server 8080 --bind 127.0.0.1 --directory . & \
	sleep 0.5 && open -a Safari http://localhost:8080; \
	wait

clean:
	rm -f $(JSON) $(INDEX)
	rm -f thumbnails/*.jpg

help:
	@echo "Targets:"
	@echo "  make scan        Refresh data/drive-index.json from Google Drive"
	@echo "  make stubs       Ask Claude to insert new Drive videos into tanzpalast.yaml"
	@echo "  make build       Compile tanzpalast.yaml → data/tanzpalast-data.json"
	@echo "  make thumbnails  Extract JPEG frames from local .mov files in data/"
	@echo "  make all         thumbnails + build"
	@echo "  make preview     Serve locally on :8080 and open Safari (Ctrl+C to stop)"
	@echo "  make publish     all + git commit + push"
	@echo "  make clean       Remove generated JSON, index, and thumbnails"

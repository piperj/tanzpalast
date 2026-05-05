YAML  := tanzpalast.yaml
JSON  := data/tanzpalast-data.json
INDEX := data/drive-index.json
MOVS  := $(wildcard data/*.mov data/*.MOV)

.PHONY: all scan stubs build thumbnails publish preview clean help

all: stubs thumbnails build

# --- Drive ---

scan: $(INDEX)

$(INDEX): $(MOVS)
	uv run python src/list_drive.py

stubs: $(INDEX)
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

$(JSON): $(YAML) $(INDEX)
	uv run python src/build.py

# --- Thumbnails ---

thumbnails: $(MOVS)
	uv run python src/make_thumbnails.py

# --- Publish ---

publish: all
	git add $(YAML) $(JSON) $(INDEX) thumbnails/
	git diff --cached --quiet || git commit -m "update catalog"
	git push

# --- Misc ---

preview:
	@pkill -f "http.server" 2>/dev/null; sleep 0.5; true
	open -a Safari http://localhost:8080
	python3 -m http.server 8080 --bind 127.0.0.1 --directory "$(CURDIR)"

clean:
	rm -f $(JSON) $(INDEX)
	rm -f thumbnails/*.jpg

help:
	@echo "Workflow: drag .mov to data/ + Drive → stubs → edit YAML → publish"
	@echo ""
	@echo "  make stubs       Scan Drive + ask Claude to insert new videos into YAML"
	@echo "  make all         thumbnails + build"
	@echo "  make publish     all + git commit + push"
	@echo ""
	@echo "  make preview     Serve locally on :8080 and open Safari (Ctrl+C to stop)"
	@echo ""
	@echo "  make scan        Refresh drive-index.json (auto-triggered by make stubs)"
	@echo "  make thumbnails  Extract JPEG frames from local .mov files in data/"
	@echo "  make build       Compile tanzpalast.yaml → data/tanzpalast-data.json"
	@echo "  make clean       Remove generated JSON, index, and thumbnails"

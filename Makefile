YAML  := tanzpalast.yaml
JSON  := data/tanzpalast-data.json
INDEX := data/drive-index.json

.PHONY: all scan stubs build thumbnails publish clean

all: thumbnails build

# --- Drive ---

scan:
	uv run python src/list_drive.py

stubs: scan
	@uv run python src/new_filenames.py | while IFS= read -r fn; do \
	  echo ">> inferring placement for $$fn"; \
	  jq -n \
	    --arg fn "$$fn" \
	    --argjson idx "$$(cat $(INDEX))" \
	    --rawfile yaml $(YAML) \
	    '{filename:$$fn, drive_path:$$idx[$$fn].drive_path, yaml:$$yaml}' \
	  | claude -p "$$(cat prompts/insert_video.md)" \
	  | uv run python src/apply_insert.py \
	  || echo "  !! $$fn failed (see data/scan-failures.log)"; \
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

clean:
	rm -f $(JSON) $(INDEX)
	rm -f thumbnails/*.jpg

#!/bin/bash
# Watch qwen2.5:7b transfer to 4080S, then register manifest when done

TARGET_SIZE=4674078740  # 4.4 GB (exact blob size)
BLOB="sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"
SSH_OPTS="-p 19066 -o StrictHostKeyChecking=no -o ConnectTimeout=5"
REMOTE="root@175.155.64.174"

echo "[watch] Monitoring qwen2.5:7b transfer to 4080S..."

while true; do
    SIZE=$(ssh $SSH_OPTS $REMOTE "stat -c%s /root/.ollama/models/blobs/$BLOB 2>/dev/null || echo 0")
    PCT=$(awk "BEGIN {printf \"%.1f\", $SIZE / $TARGET_SIZE * 100}")
    SPEED_MB=$(awk "BEGIN {printf \"%.1f\", ($SIZE - ${LAST_SIZE:-0}) / 30 / 1048576}")
    LAST_SIZE=$SIZE

    echo "[$(date +%H:%M:%S)] ${PCT}% — $(numfmt --to=iec $SIZE) / $(numfmt --to=iec $TARGET_SIZE) @ ${SPEED_MB} MB/s"

    if [ "$SIZE" -ge "$TARGET_SIZE" ]; then
        echo "[watch] ✅ Transfer complete! Registering manifest..."

        # Copy manifest from Mac
        scp $SSH_OPTS \
          ~/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5/7b \
          $REMOTE:/root/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5/7b

        # Verify Ollama sees it
        ssh $SSH_OPTS $REMOTE "ollama list" 2>/dev/null
        echo "[watch] 🎉 qwen2.5:7b ready on 4080S!"
        break
    fi

    sleep 30
done

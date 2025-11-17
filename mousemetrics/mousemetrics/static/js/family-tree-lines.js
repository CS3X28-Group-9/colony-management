window.addEventListener("load", () => {
    const svg = document.getElementById("tree-lines");
    const wrapper = document.getElementById("tree-wrapper");
    if (!svg || !wrapper) return;

    const boxes = document.querySelectorAll("[data-mouse-id]");
    const wrapperRect = wrapper.getBoundingClientRect();

    function drawLine(x1, y1, x2, y2) {
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", x1);
        line.setAttribute("y1", y1);
        line.setAttribute("x2", x2);
        line.setAttribute("y2", y2);
        line.setAttribute("stroke", "black");
        line.setAttribute("stroke-width", "2");
        svg.appendChild(line);
    }

    function getCenterCoords(elem) {
        const r = elem.getBoundingClientRect();
        return {
            topX: r.left + r.width / 2 - wrapperRect.left,
            topY: r.top - wrapperRect.top,
            bottomX: r.left + r.width / 2 - wrapperRect.left,
            bottomY: r.bottom - wrapperRect.top,
        };
    }

    boxes.forEach((box) => {
        const mouseId = box.dataset.mouseId;
        const fatherId = box.dataset.fatherId;
        const motherId = box.dataset.motherId;

        if (!mouseId) return;

        const childCoords = getCenterCoords(box);

        if (fatherId) {
            const fatherElem = document.getElementById(`mouse-${fatherId}`);
            if (fatherElem) {
                const parentCoords = getCenterCoords(fatherElem);
                drawLine(
                    parentCoords.bottomX,
                    parentCoords.bottomY,
                    childCoords.topX,
                    childCoords.topY
                );
            }
        }

        if (motherId) {
            const motherElem = document.getElementById(`mouse-${motherId}`);
            if (motherElem) {
                const parentCoords = getCenterCoords(motherElem);
                drawLine(
                    parentCoords.bottomX,
                    parentCoords.bottomY,
                    childCoords.topX,
                    childCoords.topY
                );
            }
        }
    });
});

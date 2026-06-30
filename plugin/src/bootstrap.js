// Paper Summary Bridge —— 极简 Zotero bootstrap 插件
// 注册一个本地 HTTP endpoint，把 AI 解读报告 PDF 作为 imported_file 附件
// 挂到指定附件 key 所属的论文条目下。走官方 importFromFile API，零损库风险。

const ENDPOINT = "/paper-bridge/attach";

function startup({ id, version, rootURI }) {
    Zotero.Server.Endpoints[ENDPOINT] = function () {};
    Zotero.Server.Endpoints[ENDPOINT].prototype = {
        supportedMethods: ["POST"],
        supportedDataTypes: ["application/json"],
        // req.data: { attachmentKey: storage 目录名, reportPath: 报告 PDF 绝对路径, title?: 附件标题 }
        init: async function (req) {
            try {
                const data = req.data || {};
                const { attachmentKey, reportPath, title } = data;
                if (!attachmentKey || !reportPath) {
                    return [400, "text/plain", "缺少 attachmentKey 或 reportPath"];
                }

                const lib = Zotero.Libraries.userLibraryID;
                // 用传入的附件 key 反查它所属的论文条目
                const att = await Zotero.Items.getByLibraryAndKeyAsync(lib, attachmentKey);
                if (!att) return [404, "text/plain", "attachmentKey not found: " + attachmentKey];

                const parentID = att.parentItemID;
                if (!parentID) return [400, "text/plain", "该 key 没有父条目，无法挂载"];

                const newAtt = await Zotero.Attachments.importFromFile({
                    file: reportPath,
                    parentItemID: parentID,
                    contentType: "application/pdf"
                });

                if (title) {
                    newAtt.setField("title", title);
                    await newAtt.saveTx();
                }

                const parent = Zotero.Items.get(parentID);
                return [200, "application/json", JSON.stringify({
                    ok: true,
                    newAttachmentKey: newAtt.key,
                    parentKey: parent ? parent.key : null
                })];
            } catch (e) {
                return [500, "text/plain", "bridge error: " + (e && e.message ? e.message : String(e))];
            }
        }
    };
}

function shutdown() {
    if (typeof Zotero !== "undefined" && Zotero.Server && Zotero.Server.Endpoints[ENDPOINT]) {
        delete Zotero.Server.Endpoints[ENDPOINT];
    }
}

function install() {}
function uninstall() {}

import Foundation
import GRDB

final class RulesRepository {
    private let dbQueue: DatabaseQueue

    init(path: String) throws {
        var config = Configuration()
        config.readonly = true
        dbQueue = try DatabaseQueue(path: path, configuration: config)
    }

    static func bundled() throws -> RulesRepository {
        guard let url = Bundle.main.url(forResource: "benchside", withExtension: "db") else {
            throw NSError(domain: "Benchside", code: 1, userInfo: [
                NSLocalizedDescriptionKey: "Rules database missing from app bundle"])
        }
        return try RulesRepository(path: url.path)
    }

    func documents() throws -> [DocumentInfo] {
        try dbQueue.read { db in
            try Row.fetchAll(db, sql: "SELECT id, prefix, title, version, published FROM documents ORDER BY id")
                .map { DocumentInfo(id: $0["id"], prefix: $0["prefix"], title: $0["title"],
                                    version: $0["version"], published: $0["published"]) }
        }
    }

    func search(_ raw: String, scope: SearchScope, limit: Int = 30) throws -> [SearchHit] {
        guard let match = QuerySanitizer.ftsMatch(raw) else { return [] }
        return try dbQueue.read { db in
            // char(57344)/char(57345) are U+E000/U+E001 — must stay in sync
            // with SnippetHighlighter.start/end.
            var sql = """
                SELECT s.id, s.doc_id, s.parent_id, s.number, s.title, s.body, s.breadcrumb, s.sort_order,
                       snippet(sections_fts, 1, char(57344), char(57345), '…', 14) AS snip
                FROM sections_fts f JOIN sections s ON s.rowid = f.rowid
                WHERE sections_fts MATCH ?
                """
            var args: [DatabaseValueConvertible] = [match]
            if let docIds = scope.docIds {
                sql += " AND s.doc_id IN (\(docIds.map { _ in "?" }.joined(separator: ",")))"
                args.append(contentsOf: docIds)
            }
            sql += " ORDER BY bm25(sections_fts, 10.0, 1.0) LIMIT ?"
            args.append(limit)
            return try Row.fetchAll(db, sql: sql, arguments: StatementArguments(args))
                .map { SearchHit(section: Self.section(from: $0), snippet: $0["snip"]) }
        }
    }

    func section(id: String) throws -> RuleSection? {
        try dbQueue.read { db in
            try Row.fetchOne(db, sql: Self.sectionSQL + " WHERE id = ?", arguments: [id])
                .map(Self.section(from:))
        }
    }

    func neighbors(of section: RuleSection) throws -> (prev: RuleSection?, next: RuleSection?) {
        try dbQueue.read { db in
            let prev = try Row.fetchOne(db, sql: Self.sectionSQL +
                " WHERE doc_id = ? AND sort_order < ? ORDER BY sort_order DESC LIMIT 1",
                arguments: [section.docId, section.sortOrder]).map(Self.section(from:))
            let next = try Row.fetchOne(db, sql: Self.sectionSQL +
                " WHERE doc_id = ? AND sort_order > ? ORDER BY sort_order ASC LIMIT 1",
                arguments: [section.docId, section.sortOrder]).map(Self.section(from:))
            return (prev, next)
        }
    }

    func crossReferences(from id: String) throws -> [RuleSection] {
        try dbQueue.read { db in
            try Row.fetchAll(db, sql: Self.sectionSQL +
                " WHERE id IN (SELECT to_id FROM xrefs WHERE from_id = ?) ORDER BY sort_order",
                arguments: [id]).map(Self.section(from:))
        }
    }

    func sectionCounts() throws -> [String: Int] {
        try dbQueue.read { db in
            var counts: [String: Int] = [:]
            for row in try Row.fetchAll(db, sql: "SELECT doc_id, COUNT(*) AS n FROM sections GROUP BY doc_id") {
                counts[row["doc_id"]] = row["n"]
            }
            return counts
        }
    }

    func documentInfo(id: String) throws -> DocumentInfo? {
        try dbQueue.read { db in
            try Row.fetchOne(db, sql: "SELECT id, prefix, title, version, published FROM documents WHERE id = ?",
                             arguments: [id])
                .map { DocumentInfo(id: $0["id"], prefix: $0["prefix"], title: $0["title"],
                                    version: $0["version"], published: $0["published"]) }
        }
    }

    func sections(inDocument docId: String) throws -> [RuleSection] {
        try dbQueue.read { db in
            try Row.fetchAll(db, sql: Self.sectionSQL + " WHERE doc_id = ? ORDER BY sort_order",
                             arguments: [docId]).map(Self.section(from:))
        }
    }

    private static let sectionSQL =
        "SELECT id, doc_id, parent_id, number, title, body, breadcrumb, sort_order, structure FROM sections"

    private static func section(from row: Row) -> RuleSection {
        RuleSection(id: row["id"], docId: row["doc_id"], parentId: row["parent_id"],
                    number: row["number"], title: row["title"], body: row["body"],
                    breadcrumb: row["breadcrumb"], sortOrder: row["sort_order"],
                    structure: RuleStructure.decode(row["structure"]))
    }
}

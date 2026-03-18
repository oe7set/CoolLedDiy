"""
LZSS-Kompression für CoolLed M/U/UX-Geräte.

Port der CoolledMUtils.LzssCompress Klasse (Java-Zeilen 611-857).

Algorithmus-Kennzahlen:
- Window-Größe N = 512 (zirkulärer Buffer)
- Max Match-Länge F = 18
- Threshold = 2 (Mindest-Matchlänge 3 für Encoding)
- Buffer-Offset: N - F = 494
- Encoding: Flag-Byte (8 Bits: 1=Literal, 0=Match) + bis zu 8 Items
- Match: 2 Bytes [pos_low, (pos_high_nibble << 4) | (length - 3)]
- Literal: 1 Byte
"""

# Algorithmus-Konstanten (identisch mit Java)
N = 512          # Window-Größe (zirkulärer Buffer)
F = 18           # Max Match-Länge
THRESHOLD = 2    # Mindest-Match für Encoding (Match ab Länge 3)
NIL = N          # Null-Zeiger im Baum (512)


def lzss_compress(data: bytes) -> bytes:
    """LZSS-Kompression für CoolLed M/U/UX-Geräte.

    Exakter Port von CoolledMUtils.LzssCompress.lazssCompress().

    Args:
        data: Unkomprimierte Daten

    Returns:
        Komprimierte Daten, oder leere Bytes bei leerer Eingabe
    """
    if not data:
        return b""

    length = len(data)

    # Zirkulärer Buffer: 0..N-1 für Window, N..N+F-1 als Lookahead-Kopie
    enbuffer = bytearray(N + F + 1)

    # Binärer Suchbaum für Matching
    lson = [0] * (N + 1)
    rson = [0] * (N + 257)  # N+256+1, Nodes 513-768 als Root-Pool
    dad = [0] * (N + 1)

    # --- Baum initialisieren (InitTree) ---
    for i in range(N + 1, N + 257):
        rson[i] = NIL
    for i in range(N):
        dad[i] = NIL

    # Nicht-lokale Variablen für InsertNode/DeleteNode (als Liste für Mutability)
    match_length = [0]
    match_position = [0]

    def insert_node(r: int) -> None:
        """Fügt Position r in den Suchbaum ein und findet den besten Match.

        Entspricht InsertNode() in Java (Zeilen 635-689).
        Setzt match_length und match_position als Seiteneffekt.
        """
        # Byte.toUnsignedInt() → & 0xFF
        p = (enbuffer[r] & 0xFF) + N + 1
        lson[r] = NIL
        rson[r] = NIL
        match_length[0] = 0
        cmp = 1

        while True:
            if cmp >= 0:
                if rson[p] == NIL:
                    rson[p] = r
                    dad[r] = p
                    return
                q = rson[p]
            else:
                if lson[p] == NIL:
                    lson[p] = r
                    dad[r] = p
                    return
                q = lson[p]

            p = q
            # Vergleiche Bytes ab Position 1 (Position 0 wurde für Baum-Routing genutzt)
            i = 1
            while i < F:
                cmp = (enbuffer[r + i] & 0xFF) - (enbuffer[p + i] & 0xFF)
                if cmp != 0:
                    break
                i += 1
            else:
                # Voller Match (i == F)
                i = F

            if i > match_length[0]:
                match_position[0] = p
                match_length[0] = i
                if i >= F:
                    # Maximaler Match: Node ersetzen statt einfügen
                    dad[r] = dad[p]
                    lson[r] = lson[p]
                    rson[r] = rson[p]
                    dad[lson[p]] = r
                    dad[rson[p]] = r
                    parent = dad[p]
                    if rson[parent] == p:
                        rson[parent] = r
                    else:
                        lson[parent] = r
                    dad[p] = NIL
                    return

    def delete_node(p: int) -> None:
        """Entfernt Position p aus dem Suchbaum.

        Entspricht DeleteNode() in Java (Zeilen 691-732).
        """
        if dad[p] == NIL:
            return

        if rson[p] == NIL:
            q = lson[p]
        elif lson[p] == NIL:
            q = rson[p]
        else:
            q = lson[p]
            if rson[q] != NIL:
                while rson[q] != NIL:
                    q = rson[q]
                parent = dad[q]
                rson[parent] = lson[q]
                dad[lson[q]] = dad[q]
                lson[q] = lson[p]
                dad[lson[p]] = q
            rson[q] = rson[p]
            dad[rson[p]] = q

        dad[q] = dad[p]
        parent = dad[p]
        if rson[parent] == p:
            rson[parent] = q
        else:
            lson[parent] = q
        dad[p] = NIL

    # --- Hauptalgorithmus (lazssCompress) ---

    # Output-Buffer: Flag-Byte + bis zu 16 Daten-Bytes (8 Literale oder 8 Match-Paare)
    code_buf = bytearray(17)
    result = bytearray()

    # Buffer mit Nullen initialisieren (Positionen 0..N-F-1)
    # (bytearray ist bereits 0-initialisiert)

    # Erste F Bytes der Eingabe in Buffer laden ab Position N-F (=494)
    s = N - F  # 494 = Start-Position
    r = s
    input_pos = 0
    len_remaining = 0
    while len_remaining < F and input_pos < length:
        enbuffer[r + len_remaining] = data[input_pos]
        len_remaining += 1
        input_pos += 1

    if len_remaining == 0:
        return b""

    # Initiale Baum-Einträge für Positionen vor dem Start
    for i in range(1, F + 1):
        insert_node(s - i)
    insert_node(s)

    # Encoding-Loop
    code_buf[0] = 0
    code_buf_idx = 1
    mask = 1  # Flag-Bit-Maske (1, 2, 4, 8, 16, 32, 64, 128)
    code_buf_ptr = 0  # Delete/Write-Zeiger (Java: i10, startet bei 0)

    while True:
        if match_length[0] > len_remaining:
            match_length[0] = len_remaining

        if match_length[0] <= THRESHOLD:
            # Literal: Flag-Bit setzen (1 = Literal)
            match_length[0] = 1
            code_buf[0] |= mask
            code_buf[code_buf_idx] = enbuffer[r]
            code_buf_idx += 1
        else:
            # Match: 2 Bytes [pos_low, (pos_high<<4) | (len-3)]
            pos = match_position[0]
            code_buf[code_buf_idx] = pos & 0xFF
            code_buf[code_buf_idx + 1] = ((pos >> 4) & 0xF0) | (match_length[0] - 3)
            code_buf_idx += 2

        # Nächstes Flag-Bit
        mask = (mask << 1) & 0xFF
        if mask == 0:
            # Flag-Byte voll: Block ausgeben
            result.extend(code_buf[:code_buf_idx])
            code_buf[0] = 0
            code_buf_idx = 1
            mask = 1

        # Eingabedaten in Buffer laden und Baum aktualisieren
        last_match_length = match_length[0]
        i = 0
        while i < last_match_length and input_pos < length:
            delete_node(code_buf_ptr)
            c = data[input_pos]
            enbuffer[code_buf_ptr] = c
            # Lookahead-Kopie am Buffer-Ende
            if code_buf_ptr < F - 1:
                enbuffer[code_buf_ptr + N] = c
            code_buf_ptr = (code_buf_ptr + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            insert_node(r)
            i += 1
            input_pos += 1

        # Restliche Match-Positionen ohne neue Eingabe verarbeiten
        while i < last_match_length:
            i += 1
            delete_node(code_buf_ptr)
            code_buf_ptr = (code_buf_ptr + 1) & (N - 1)
            r = (r + 1) & (N - 1)
            len_remaining -= 1
            if len_remaining > 0:
                insert_node(r)

        if len_remaining <= 0:
            break

    # Letzten unvollständigen Block ausgeben
    if code_buf_idx > 1:
        result.extend(code_buf[:code_buf_idx])

    return bytes(result)

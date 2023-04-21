import chess


def polyglot_move(board, move):
    if move.promotion:
        return (move.promotion-1) << 12 | move.to_square | move.from_square << 6
    if move.from_square == chess.E1 or move.from_square == chess.E8 and board.is_castling(move):            
        if move.to_square == chess.G1: move.to_square = chess.H1               
        elif move.to_square == chess.C1: move.to_square = chess.A1               
        elif move.to_square == chess.G8: move.to_square = chess.H8
        elif move.to_square == chess.C8: move.to_square = chess.A8
    return move.to_square | move.from_square << 6


def original_move(raw_move):
    to_square = raw_move & 63
    from_square = (raw_move >> 6) & 63
    promotion_part = (raw_move >> 12) & 7
    promotion = promotion_part + 1 if promotion_part else None
    if from_square == to_square: promotion, drop = None, promotion
    else: drop = None
    return chess.Move(from_square, to_square, promotion, drop)

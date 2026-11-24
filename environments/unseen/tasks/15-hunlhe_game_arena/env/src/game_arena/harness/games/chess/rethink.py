                                        
 
                                                                 
                                                                  
                                         
 
                                                
 
                                                                     
                                                                   
                                                                          
                                                                     
                                

                                                                       

import chess
from game_arena.harness import rethink
import re


def rule_explain_illegal_move(*, fen: str, move_str: str):
  pass                                                                                                  

       
                                                             
                                                                         
               

          
                                                                            
                                                       
     
  board = chess.Board(fen)

                                         
  try:
                                                                      
    move = chess.Move.from_uci(move_str)
  except ValueError:
                                                                   
    try:
      move = board.parse_san(move_str)
    except ValueError as parse_san_error:
                                           
      error_msg = str(parse_san_error)
      if "ambiguous" in error_msg:
                                                
        try:
                                                         
          p_match = re.match(
              r"([NBRQK])?([a-h]?[1-8]?)?x?([a-h][1-8])", move_str
          )
          if p_match is None:
            raise ValueError(f"Invalid SAN: {move_str}") from parse_san_error
          else:
            piece_char, _, to_square_name = p_match.groups()

          piece_type = (
              chess.PIECE_SYMBOLS.index(piece_char.lower())
              if piece_char
              else chess.PAWN
          )
          to_square = chess.SQUARE_NAMES.index(to_square_name)

          ambiguous_pieces = []
          for legal_move in board.legal_moves:
            piece = board.piece_at(legal_move.from_square)
            if (
                legal_move.to_square == to_square
                and piece is not None
                and piece.piece_type == piece_type
            ):
              ambiguous_pieces.append(chess.square_name(legal_move.from_square))

          return (
              f"Invalid SAN: The move '{move_str}' is ambiguous. "
              f"The following pieces can also move to {to_square_name}: "
              f"{', '.join(ambiguous_pieces)}. "
              "Please specify the starting file or rank (e.g., 'Rha1')."
          )
        except (ValueError, AttributeError, TypeError):
          return (
              f"Invalid SAN: The move '{move_str}' is ambiguous. "
              "Please be more specific."
          )

      elif "illegal" in error_msg:
                                                        
                                                                     
                                                                
                                  
        if move_str[0] in "abcdefgh":
          return (
              f"Invalid SAN: The move '{move_str}' is interpreted as a pawn"
              " move, which is illegal in this position. If you intended to"
              f" move a piece to {move_str[-2:]}, you must specify which piece"
              f" (e.g., 'N{move_str[-2:]}', 'B{move_str[-2:]}')."
          )
        else:
          return (
              f"Invalid SAN: The move '{move_str}' is illegal. The specified"
              " piece cannot legally make that move in this position."
          )
      else:
        return f"The move '{move_str}' is invalid. Reason: {parse_san_error}"

                                                       
  if move in board.legal_moves:
    return f"The move {move.uci()} is legal."

                                                                  
  from_square = move.from_square
  to_square = move.to_square
  piece = board.piece_at(from_square)

                                   
  if piece is None:
    return (
        "Illegal Move: There is no piece on the starting square "
        f"({chess.square_name(from_square)})."
    )

                                          
  if piece.color != board.turn:
    turn_color = "White" if board.turn == chess.WHITE else "Black"
    return (
        f"Illegal Move: It is {turn_color}'s turn to move, but the piece on "
        f"{chess.square_name(from_square)} is not theirs."
    )

                                         
  target_piece = board.piece_at(to_square)
  if target_piece and target_piece.color == piece.color:
    return (
        f"Illegal Move: The square {chess.square_name(to_square)} is occupied"
        " by a friendly piece."
    )

                           
                                                                  
                        
  if move in board.pseudo_legal_moves:
    return "Illegal Move: This move would leave the king in check."

                                                                     
  piece_type = piece.piece_type

                       
  if piece_type == chess.KING:
    if board.is_castling(move):
      if board.is_check():
        return "Illegal Castling: You cannot castle while in check."
                               
      for sq in chess.SquareSet(chess.between(from_square, to_square)):
        if board.is_attacked_by(not board.turn, sq):
          return (
              "Illegal Castling: The king cannot pass through an attacked"
              f" square ({chess.square_name(sq)})."
          )
    return (
        "Illegal King Move: The king can only move to adjacent squares and"
        " cannot move into check."
    )

                         
  if piece_type == chess.KNIGHT:
    return (
        "Illegal Knight Move: A knight moves in an 'L' shape (two squares in"
        " one direction, then one perpendicularly)."
    )

                       
  if piece_type == chess.PAWN:
                                 
    if target_piece is None and chess.square_file(
        from_square
    ) != chess.square_file(to_square):
      if not board.is_en_passant(move):
        return "Illegal Pawn Move: Pawns can only capture diagonally."
                                                   
    if target_piece is not None and chess.square_file(
        from_square
    ) == chess.square_file(to_square):
      return (
          "Illegal Pawn Move: Pawns cannot capture by moving straight forward."
      )
    return (
        "Illegal Pawn Move: Pawns have specific rules for moving forward and"
        " capturing."
    )

                                        
  if piece_type in (chess.ROOK, chess.BISHOP, chess.QUEEN):
                              
    for sq in chess.SquareSet(chess.between(from_square, to_square)):
      if board.piece_at(sq) is not None:
        blocker_sq_name = chess.square_name(sq)
        return (
            "Illegal Move: The path is blocked by a piece on"
            f" {blocker_sq_name}."
        )

                                                                    
    if piece_type == chess.ROOK:
      return (
          "Illegal Rook Move: A rook can only move horizontally or vertically."
      )
    if piece_type == chess.BISHOP:
      return "Illegal Bishop Move: A bishop can only move diagonally."
    if piece_type == chess.QUEEN:
      return (
          "Illegal Queen Move: The queen's path is clear, but the move is not a"
          " valid straight or diagonal line."
      )

  return (
      "Illegal Move: The move violates the rules of chess for an unknown"
      " reason."
  )


class RethinkSampler(rethink.RethinkSampler):
  pass                            

  def explain_illegal_move(self, move_str):
    return rule_explain_illegal_move(
        fen=self._game_adapter.get_readable_state(representation_type="fen"),
        move_str=move_str,
    )

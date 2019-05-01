;;; THIS FILE IS NOT MY OWN, AND EXITS IN THE PUBLIC DOMAIN.
;;; THIS FILE MEANT PURELY FOR OBSERVATIONAL AND COMPARATIVE PURPOSE.

(defun SPLIT-LIST (L)
  (if (endp L)
      '(nil nil)
    (let ((X (SPLIT-LIST (CDR L))))
      (list  (cons (CAR L)(CADR X)) (CAR X) ))))

(defun MERGE-LISTS (L1 L2)
  (cond
   ((and(endp L1 )(endp L2)) nil )
   ((endp L1) (cons (CAR L2) (MERGE-LISTS nil (CDR L2))))
   ((endp L2) (cons (CAR L1) (MERGE-LISTS (CDR L1) nil)))
   ((< (CAR L1) (CAR L2)) (cons (CAR L1) (MERGE-LISTS (CDR L1) L2  )))
   ((>= (CAR L1) (CAR L2)) (cons (CAR L2) (MERGE-LISTS L1 (CDR L2))  ))))

(defun MSORT (L)
  (cond ((endp L) nil)
        ((endp (CDR L)) L)
        (t
         (let* ((S (SPLIT-LIST L ))
                (L1 (CAR S))
                (L2 (CADR S))
                (X (MSORT L1))
                (Y (MSORT L2)))
           (MERGE-LISTS X Y)))))

(let* ((UNSORTED '(8 3 1 7 4 9 1 3 5 2 6))
       (SORTED (MSORT UNSORTED)))
  (format t "Unsorted List: '(~{~a~^ ~})~%" UNSORTED)
  (format t "  Sorted List: '(~{~a~^ ~})~%" SORTED))

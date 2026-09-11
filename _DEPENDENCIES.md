

task next 5 "thing"
task chain 5 "thing 1" "thing 3" "thing 4"
task depends 5 3 -- add a dependency of 3 on 5
task undepends 5 3 -- remove the depenency of 3 on 5



task delete 7 -> deletes the node and repairs the chain
task delete 8 --forward -> deletes the node onwards




Core attributes:
- every chain must have a head
- every head must have a parent
- links are bidirectional
- Organize based on first link
    - if i allowed multiple, i could organize based on first link? lets do that
- 





            1 Parent


    2 child1 (head)             3 child2
      |
    4 dep1
      |
    5 dep2
      |
    6 dep3

        7 dep3-child1 (head)
            |
        8 dep3-child1-dep1  (also depends on: 3)
            |
        9 dep3-child1-dep2 

        10 dep3-child2
        
        11 dep3-child3



If i delete 7?  8 takes his place and becomes child of dep3
    - becomes the head of the chain, inherits the parent
If i delete 8?  9 depends on 7

If i undepend 8 from 7? 8 shows under 3

if i delete 6? it all goes
    - delete checks if head and if so rolls through the chain. If there's no dependency, it gets deleted


DB methods:
    - add_dependency(src_id, parent_id)
    - delete_dependency(src_id, parent_id)
    - delete_chain(head_id)
        - goes through and deletes everything pointed to by the chain
        - clears all of the item dependencies

Updates to existing:
    - delete needs to check if subelements are heads of a chain and if so, call delete chain on them
    - delete needs to check if this item has dependencies and if so, call the requisite dependency calls
    - delete needs to check if the item was the head of a chain - if so, its first dependency needs to become the head of the chain
        - how do we resolve dependencies?


                B       A

                |   \   |
                |    \  |
                |     \ | 
                D       C
                        |
                        |
                        |
                        E

            Say B adds C as a dependency - is C part of As chain or Bs chain? Presumably, it would be based on whoever added it first

            If i:
                create A
                next A C     -->  C.depends_on[A], A.depended_by[C], C shows under A
                depend B C   -->  C.depends_on[A,B]

                if we
                    delete A     -->  C.depends_on[B], B needs to become the head of the chain (or should C?)
                
                if we
                    delete-chain B --> B is not the head, so shouldn't matter
                    
                
